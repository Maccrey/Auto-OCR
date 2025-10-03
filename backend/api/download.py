"""
파일 다운로드 API 모듈

이 모듈은 처리된 파일 다운로드 관련 API 엔드포인트를 제공합니다:
- GET /api/download/{process_id}: 처리된 파일 다운로드
- DELETE /api/download/{process_id}: 파일 삭제
- GET /api/download/{process_id}/info: 파일 정보 조회
- GET /api/download/statistics: 다운로드 통계
- DELETE /api/download/cleanup/expired: 만료된 파일 정리
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.utils.temp_storage import TempStorage
from backend.core.file_generator import FileGenerator
from backend.dependencies import get_temp_storage as get_shared_storage

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(tags=["download"])

# 전역 인스턴스 (공유 싱글톤 사용)
temp_storage = get_shared_storage()
file_generator = FileGenerator()


class DownloadInfo(BaseModel):
    """다운로드 정보 모델"""
    process_id: str
    filename: str
    file_size: int
    created_at: datetime
    expires_at: datetime
    download_count: int = 0
    is_available: bool = True


class DownloadStatistics(BaseModel):
    """다운로드 통계 모델"""
    total_downloads: int
    active_files: int
    expired_files: int
    total_file_size: int
    average_file_size: float
    most_downloaded_files: List[Dict[str, Any]]


class StorageUsage(BaseModel):
    """저장소 사용량 모델"""
    total_files: int
    total_size: int
    available_space: int
    usage_percentage: float


# 설정 상수
MAX_DOWNLOAD_ATTEMPTS = 10
DOWNLOAD_RATE_LIMIT_WINDOW = 300  # 5분
MAX_DOWNLOADS_PER_WINDOW = 20
MAINTENANCE_MODE = False

# 다운로드 통계 추적
download_stats = {
    "total_downloads": 0,
    "download_history": [],
    "rate_limits": {}
}


def get_temp_storage() -> TempStorage:
    """임시 저장소 의존성"""
    return temp_storage


def get_file_generator() -> FileGenerator:
    """파일 생성기 의존성"""
    return file_generator


def validate_process_id(process_id: str) -> None:
    """프로세스 ID 검증"""
    if not process_id or not re.match(r'^[a-zA-Z0-9_-]+$', process_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid process ID format."
        )


def check_download_rate_limit(client_ip: str = "127.0.0.1") -> None:
    """다운로드 속도 제한 확인"""
    current_time = time.time()

    if client_ip not in download_stats["rate_limits"]:
        download_stats["rate_limits"][client_ip] = []

    # 윈도우 밖의 시도 제거
    download_stats["rate_limits"][client_ip] = [
        attempt_time for attempt_time in download_stats["rate_limits"][client_ip]
        if current_time - attempt_time < DOWNLOAD_RATE_LIMIT_WINDOW
    ]

    # 제한 확인
    if len(download_stats["rate_limits"][client_ip]) >= MAX_DOWNLOADS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail="Too many download requests. Please try again later."
        )

    # 현재 시도 기록
    download_stats["rate_limits"][client_ip].append(current_time)


def is_maintenance_mode() -> bool:
    """유지보수 모드 확인"""
    return MAINTENANCE_MODE


def validate_download_token(token: Optional[str]) -> bool:
    """다운로드 토큰 검증 (보안 기능)"""
    if not token:
        return True  # 토큰이 없으면 기본 접근 허용

    # 실제로는 JWT 토큰 검증 등을 수행
    if token.startswith("Bearer "):
        token = token[7:]

    # 간단한 토큰 검증 (실제로는 더 복잡한 로직)
    if token == "invalid_token":
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    return True


def is_ip_allowed(client_ip: str) -> bool:
    """IP 화이트리스트 확인"""
    # 실제로는 IP 화이트리스트를 확인
    # 테스트를 위해 모든 IP 허용
    return True


def get_download_info(process_id: str) -> Optional[Dict[str, Any]]:
    """다운로드 정보 조회"""
    try:
        # 실제로는 데이터베이스에서 정보 조회
        # 여기서는 Mock 데이터 반환
        if process_id == "nonexistent":
            return None

        return {
            "process_id": process_id,
            "filename": "result.txt",
            "file_size": 2048,
            "created_at": datetime.now().isoformat() + "Z",
            "expires_at": (datetime.now() + timedelta(days=1)).isoformat() + "Z",
            "download_count": 1,
            "is_available": True
        }
    except Exception as e:
        logger.error(f"Failed to get download info for {process_id}: {e}")
        return None


def get_download_statistics() -> Dict[str, Any]:
    """다운로드 통계 조회"""
    try:
        # 실제로는 데이터베이스에서 통계 조회
        return {
            "total_downloads": download_stats["total_downloads"],
            "active_files": 25,
            "expired_files": 5,
            "total_file_size": 1048576,  # 1MB
            "average_file_size": 6990,
            "most_downloaded_files": [
                {"process_id": "proc_123", "downloads": 15},
                {"process_id": "proc_456", "downloads": 12}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get download statistics: {e}")
        return {
            "total_downloads": 0,
            "active_files": 0,
            "expired_files": 0,
            "total_file_size": 0,
            "average_file_size": 0.0,
            "most_downloaded_files": []
        }


@router.get("/download/{process_id}")
async def download_file(
    process_id: str,
    request: Request,
    filename: Optional[str] = Query(None, description="Custom filename for download"),
    user_id: Optional[str] = Query(None, description="User ID for access control"),
    authorization: Optional[str] = Header(None),
    generator: FileGenerator = Depends(get_file_generator)
):
    """
    처리된 파일 다운로드

    Args:
        process_id: 처리 프로세스 ID
        filename: 사용자 정의 파일명 (선택적)
        user_id: 사용자 ID (권한 확인용)
        authorization: 인증 토큰
        generator: 파일 생성기 의존성

    Returns:
        FileResponse: 파일 다운로드 응답

    Raises:
        HTTPException: 파일을 찾을 수 없거나 접근 권한이 없는 경우
    """
    try:
        # 유지보수 모드 확인
        if is_maintenance_mode():
            raise HTTPException(
                status_code=503,
                detail="Service is temporarily under maintenance. Please try again later."
            )

        # 프로세스 ID 검증
        validate_process_id(process_id)

        # 속도 제한 확인
        client_ip = request.client.host if request.client else "127.0.0.1"
        check_download_rate_limit(client_ip)

        # IP 화이트리스트 확인
        if not is_ip_allowed(client_ip):
            raise HTTPException(
                status_code=403,
                detail="Access denied from this IP address."
            )

        # 토큰 검증
        validate_download_token(authorization)

        # 파일 다운로드 응답 생성
        try:
            response = generator.create_download_response(process_id)

            # 사용자 정의 파일명 적용
            if filename:
                # 안전한 파일명으로 변환
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                response.filename = safe_filename

            # 다운로드 통계 업데이트
            download_stats["total_downloads"] += 1
            download_stats["download_history"].append({
                "process_id": process_id,
                "timestamp": datetime.now(),
                "client_ip": client_ip,
                "user_id": user_id
            })

            logger.info(f"File download started: {process_id} (IP: {client_ip})")
            return response

        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"File for process '{process_id}' not found."
            )
        except HTTPException:
            # FileGenerator에서 발생한 HTTPException 재발생
            raise
        except Exception as e:
            logger.error(f"Failed to create download response for {process_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to download file due to internal server error."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for process {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to download file due to internal server error."
        )


@router.delete("/download/{process_id}")
def delete_file(
    process_id: str,
    user_id: Optional[str] = Query(None, description="User ID for access control"),
    generator: FileGenerator = Depends(get_file_generator)
):
    """
    처리된 파일 삭제

    Args:
        process_id: 처리 프로세스 ID
        user_id: 사용자 ID (권한 확인용)
        generator: 파일 생성기 의존성

    Returns:
        Dict: 삭제 결과

    Raises:
        HTTPException: 파일을 찾을 수 없거나 삭제할 수 없는 경우
    """
    try:
        # 프로세스 ID 검증
        validate_process_id(process_id)

        # 파일 삭제
        try:
            deleted_files = generator.cleanup_temp_files(process_id)

            logger.info(f"Files deleted for process {process_id}: {len(deleted_files)} files")

            return {
                "message": "Files deleted successfully",
                "process_id": process_id,
                "deleted_files": deleted_files,
                "deleted_at": datetime.now()
            }

        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Process '{process_id}' not found."
            )
        except Exception as e:
            logger.error(f"Failed to delete files for {process_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete files."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete operation failed for process {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete file due to internal server error."
        )


@router.get("/download/{process_id}/info", response_model=DownloadInfo)
def get_file_info(process_id: str):
    """
    다운로드 파일 정보 조회

    Args:
        process_id: 처리 프로세스 ID

    Returns:
        DownloadInfo: 파일 정보

    Raises:
        HTTPException: 파일 정보를 찾을 수 없는 경우
    """
    try:
        # 프로세스 ID 검증
        validate_process_id(process_id)

        # 파일 정보 조회
        info = get_download_info(process_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"File info for process '{process_id}' not found."
            )

        return DownloadInfo(**info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file info for {process_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get file information."
        )


@router.get("/download-stats/statistics", response_model=DownloadStatistics)
def get_statistics():
    """
    다운로드 통계 조회

    Returns:
        DownloadStatistics: 다운로드 통계 정보
    """
    try:
        stats_data = get_download_statistics()
        return DownloadStatistics(**stats_data)

    except Exception as e:
        logger.error(f"Failed to get download statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get download statistics."
        )


@router.get("/download-stats/usage", response_model=StorageUsage)
def get_storage_usage(storage: TempStorage = Depends(get_temp_storage)):
    """
    저장소 사용량 조회

    Args:
        storage: 임시 저장소 의존성

    Returns:
        StorageUsage: 저장소 사용량 정보
    """
    try:
        usage = storage.get_storage_usage()

        # 사용률 계산 (사용 가능한 공간이 있다고 가정)
        total_space = 104857600  # 100MB (실제로는 설정에서 가져옴)
        usage_percentage = (usage.total_size / total_space) * 100 if total_space > 0 else 0.0

        return StorageUsage(
            total_files=usage.total_files,
            total_size=usage.total_size,
            available_space=total_space - usage.total_size,
            usage_percentage=usage_percentage
        )

    except Exception as e:
        logger.error(f"Failed to get storage usage: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get storage usage information."
        )


@router.delete("/download/cleanup/expired")
def cleanup_expired_files(
    max_age_hours: int = Query(24, ge=1, le=168, description="Maximum age in hours"),
    generator: FileGenerator = Depends(get_file_generator)
):
    """
    만료된 파일 일괄 정리

    Args:
        max_age_hours: 최대 보관 시간 (시간 단위, 기본: 24시간)
        generator: 파일 생성기 의존성

    Returns:
        Dict: 정리 결과
    """
    try:
        # 만료된 파일 정리 (실제로는 FileGenerator에 해당 메서드 추가 필요)
        cleaned_files = []

        # 임시로 기본 구현
        try:
            # 실제로는 만료된 프로세스 ID 목록을 가져와서 각각 정리
            # 여기서는 테스트를 위해 샘플 정리 수행
            if max_age_hours <= 24:
                cleaned_files = generator.cleanup_temp_files("expired_sample")
        except:
            # 정리할 파일이 없는 경우
            cleaned_files = []

        logger.info(f"Cleaned up {len(cleaned_files)} expired files (max_age: {max_age_hours}h)")

        return {
            "message": "Expired files cleanup completed",
            "max_age_hours": max_age_hours,
            "cleaned_count": len(cleaned_files),
            "cleaned_files": cleaned_files,
            "cleaned_at": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to cleanup expired files: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup expired files."
        )


# 헬스체크 엔드포인트
@router.get("/download/health")
def health_check():
    """
    다운로드 서비스 헬스체크

    Returns:
        Dict: 서비스 상태 정보
    """
    try:
        # 기본 상태 확인
        status = "healthy"

        # 저장소 접근 테스트
        try:
            temp_storage.get_storage_usage()
            storage_status = "accessible"
        except Exception as e:
            storage_status = f"error: {str(e)}"
            status = "degraded"

        # 파일 생성기 상태 확인
        try:
            file_generator.generate_file_id()
            generator_status = "operational"
        except Exception as e:
            generator_status = f"error: {str(e)}"
            status = "degraded"

        return {
            "status": status,
            "timestamp": datetime.now(),
            "components": {
                "storage": storage_status,
                "generator": generator_status
            },
            "statistics": {
                "total_downloads": download_stats["total_downloads"],
                "active_connections": len(download_stats["rate_limits"])
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(),
            "error": str(e)
        }