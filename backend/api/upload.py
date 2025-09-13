"""
파일 업로드 API 모듈

이 모듈은 PDF 파일 업로드 관련 API 엔드포인트를 제공합니다:
- POST /api/upload: PDF 파일 업로드
- GET /api/upload/{upload_id}/status: 업로드 상태 확인
- GET /api/upload/list: 업로드된 파일 목록
- DELETE /api/upload/cleanup/expired: 만료된 파일 정리
- GET /api/upload/statistics: 업로드 통계
- GET /api/upload/health: 서비스 헬스체크
"""

import os
import time
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.utils.temp_storage import TempStorage

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(tags=["upload"])

# 전역 임시 저장소 인스턴스 (실제로는 의존성 주입 사용)
temp_storage = TempStorage()


class UploadError(Exception):
    """업로드 관련 오류"""
    pass


class UploadResponse(BaseModel):
    """업로드 응답 모델"""
    upload_id: str
    filename: str
    file_size: int
    upload_time: datetime
    status: str = "uploaded"


class UploadStatusResponse(BaseModel):
    """업로드 상태 응답 모델"""
    upload_id: str
    filename: str
    file_size: int
    upload_time: datetime
    status: str


class UploadListResponse(BaseModel):
    """업로드 목록 응답 모델"""
    uploads: List[UploadStatusResponse]
    total: int
    page: int = 1
    per_page: int = 50


class UploadStatistics(BaseModel):
    """업로드 통계 모델"""
    total_uploads: int
    total_size: int
    average_file_size: float
    uploads_today: int
    success_rate: float


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    storage: Dict[str, Any]
    timestamp: datetime


# 설정 상수
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = ["application/pdf"]
ALLOWED_EXTENSIONS = [".pdf"]
MAX_FILENAME_LENGTH = 255

# 업로드 속도 제한 (간단한 구현)
upload_attempts = {}
RATE_LIMIT_WINDOW = 60  # 60초
MAX_UPLOADS_PER_WINDOW = 10


def get_temp_storage() -> TempStorage:
    """임시 저장소 의존성"""
    return temp_storage


def check_rate_limit(client_ip: str = "127.0.0.1") -> None:
    """업로드 속도 제한 확인"""
    current_time = time.time()

    if client_ip not in upload_attempts:
        upload_attempts[client_ip] = []

    # 윈도우 밖의 시도 제거
    upload_attempts[client_ip] = [
        attempt_time for attempt_time in upload_attempts[client_ip]
        if current_time - attempt_time < RATE_LIMIT_WINDOW
    ]

    # 제한 확인
    if len(upload_attempts[client_ip]) >= MAX_UPLOADS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail="Too many upload attempts. Please try again later."
        )

    # 현재 시도 기록
    upload_attempts[client_ip].append(current_time)


def validate_file_type(file: UploadFile) -> None:
    """파일 타입 검증"""
    # MIME 타입 검증
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only PDF files are allowed. Got: {file.content_type}"
        )

    # 파일 확장자 검증
    if file.filename:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension. Only {', '.join(ALLOWED_EXTENSIONS)} are allowed."
            )


def validate_file_content(content: bytes) -> None:
    """파일 내용 검증"""
    # PDF 헤더 검증
    if not content.startswith(b'%PDF-'):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file. File does not have valid PDF header."
        )

    # 기본적인 PDF 구조 검증
    if b'%%EOF' not in content:
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file. File appears to be corrupted or incomplete."
        )


def validate_file_size(file_size: int) -> None:
    """파일 크기 검증"""
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file is not allowed."
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
        )


def sanitize_filename(filename: str) -> str:
    """안전한 파일명으로 변환"""
    if not filename:
        return f"upload_{int(time.time())}.pdf"

    # 위험한 문자 제거
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_filename = re.sub(r'\.\.+', '.', safe_filename)
    safe_filename = safe_filename.strip()

    # 경로 순회 방지
    safe_filename = os.path.basename(safe_filename)

    # 파일명 길이 제한
    if len(safe_filename) > MAX_FILENAME_LENGTH:
        name = Path(safe_filename).stem[:MAX_FILENAME_LENGTH-10]
        ext = Path(safe_filename).suffix[:9]
        safe_filename = f"{name}{ext}"

    # 빈 파일명 처리
    if not safe_filename or safe_filename == '.':
        safe_filename = f"upload_{int(time.time())}.pdf"

    return safe_filename


def validate_upload_id(upload_id: str) -> None:
    """업로드 ID 검증"""
    if not upload_id or not re.match(r'^[a-zA-Z0-9_-]+$', upload_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid upload ID format."
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    PDF 파일 업로드

    Args:
        file: 업로드할 PDF 파일
        storage: 임시 저장소 의존성

    Returns:
        UploadResponse: 업로드 결과 정보

    Raises:
        HTTPException: 파일 검증 실패, 저장 실패 등
    """
    try:
        # 속도 제한 확인
        check_rate_limit()

        # 파일 존재 확인
        if not file or not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No file provided."
            )

        # 파일 읽기
        content = await file.read()
        file_size = len(content)

        # 기본 검증
        validate_file_size(file_size)
        validate_file_type(file)
        validate_file_content(content)

        # 파일명 정리
        safe_filename = sanitize_filename(file.filename)

        # 파일 저장 (uploader_id는 임시로 "web_user" 사용)
        upload_id = storage.save_file(content, safe_filename, uploader_id="web_user")

        # 응답 생성
        response = UploadResponse(
            upload_id=upload_id,
            filename=safe_filename,
            file_size=file_size,
            upload_time=datetime.now()
        )

        logger.info(f"File uploaded successfully: {upload_id} ({safe_filename}, {file_size} bytes)")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload file due to internal server error."
        )
    finally:
        # 파일 스트림 정리
        if file:
            await file.close()


@router.get("/upload/{upload_id}/status", response_model=UploadStatusResponse)
def get_upload_status(
    upload_id: str,
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    업로드 상태 확인

    Args:
        upload_id: 업로드 ID
        storage: 임시 저장소 의존성

    Returns:
        UploadStatusResponse: 업로드 상태 정보

    Raises:
        HTTPException: 업로드 ID를 찾을 수 없는 경우
    """
    try:
        # 업로드 ID 검증
        validate_upload_id(upload_id)

        # 파일 정보 조회 (user_id는 임시로 "web_user" 사용)
        file_info = storage.get_file(upload_id, user_id="web_user")

        if not file_info:
            raise HTTPException(
                status_code=404,
                detail=f"Upload with ID '{upload_id}' not found."
            )

        # 응답 생성
        return UploadStatusResponse(
            upload_id=upload_id,
            filename=file_info.filename,
            file_size=file_info.file_size,
            upload_time=file_info.created_at,
            status="uploaded"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get upload status."
        )


@router.get("/upload/list", response_model=UploadListResponse)
def get_upload_list(
    page: int = 1,
    per_page: int = 50,
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    업로드된 파일 목록 조회

    Args:
        page: 페이지 번호 (1부터 시작)
        per_page: 페이지당 항목 수 (최대 100)
        storage: 임시 저장소 의존성

    Returns:
        UploadListResponse: 업로드 목록
    """
    try:
        # 파라미터 검증
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 50

        # 파일 목록 조회 (현재 TempStorage에는 list 메서드가 없으므로 임시로 빈 목록)
        all_files = []  # TODO: TempStorage에 list_files 메서드 추가 필요
        total = len(all_files)

        # 페이지네이션
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_files = all_files[start_idx:end_idx]

        # 응답 생성
        uploads = []

        return UploadListResponse(
            uploads=uploads,
            total=total,
            page=page,
            per_page=per_page
        )

    except Exception as e:
        logger.error(f"Failed to get upload list: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get upload list."
        )


@router.delete("/upload/cleanup/expired")
def cleanup_expired_uploads(
    max_age_hours: int = 24,
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    만료된 업로드 파일 정리

    Args:
        max_age_hours: 최대 보관 시간 (기본: 24시간)
        storage: 임시 저장소 의존성

    Returns:
        Dict: 정리 결과
    """
    try:
        if max_age_hours < 1:
            max_age_hours = 24

        max_age_seconds = max_age_hours * 3600
        cleaned_files = storage.cleanup_expired_files(max_age_seconds)

        logger.info(f"Cleaned up {len(cleaned_files)} expired uploads")

        return {
            "message": "Cleanup completed successfully",
            "cleaned_count": len(cleaned_files),
            "max_age_hours": max_age_hours
        }

    except Exception as e:
        logger.error(f"Failed to cleanup expired uploads: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup expired uploads."
        )


@router.get("/upload/statistics", response_model=UploadStatistics)
def get_upload_statistics(
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    업로드 통계 조회

    Args:
        storage: 임시 저장소 의존성

    Returns:
        UploadStatistics: 업로드 통계 정보
    """
    try:
        # TODO: TempStorage에 get_statistics 메서드 추가 필요
        # 현재는 기본값 사용
        usage = storage.get_storage_usage()

        return UploadStatistics(
            total_uploads=usage.total_files,
            total_size=usage.total_size,
            average_file_size=usage.total_size / usage.total_files if usage.total_files > 0 else 0.0,
            uploads_today=0,  # TODO: 날짜별 통계 추가 필요
            success_rate=1.0   # TODO: 성공률 통계 추가 필요
        )

    except Exception as e:
        logger.error(f"Failed to get upload statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get upload statistics."
        )


@router.get("/upload/health", response_model=HealthCheckResponse)
async def health_check(
    storage: TempStorage = Depends(get_temp_storage)
):
    """
    업로드 서비스 헬스체크

    Args:
        storage: 임시 저장소 의존성

    Returns:
        HealthCheckResponse: 서비스 상태 정보
    """
    try:
        # 저장소 상태 확인
        storage_info = {
            "available": True,
            "storage_path": str(getattr(storage, 'base_path', 'unknown')),
            "disk_usage": "unknown"  # 실제 구현에서는 디스크 사용량 확인
        }

        # 간단한 동작 테스트
        test_data = b"test"
        test_id = storage.generate_file_id()

        try:
            # 테스트 파일 생성 및 삭제
            test_id = storage.save_file(test_data, f"health_check_{test_id}.test", uploader_id="health_check")
            storage.delete_file(test_id, user_id="health_check")
            storage_info["write_test"] = "passed"
        except Exception as e:
            storage_info["write_test"] = "failed"
            storage_info["available"] = False
            storage_info["error"] = str(e)

        status = "healthy" if storage_info["available"] else "unhealthy"

        return HealthCheckResponse(
            status=status,
            storage=storage_info,
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            storage={"available": False, "error": str(e)},
            timestamp=datetime.now()
        )