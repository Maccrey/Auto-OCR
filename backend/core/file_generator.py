"""
파일 생성 및 다운로드 관리 모듈

이 모듈은 OCR 결과를 파일로 생성하고 다운로드를 관리합니다:
- 텍스트 파일 생성 및 인코딩 처리
- 다운로드 응답 생성
- 임시 파일 관리 및 정리
"""

import os
import time
import tempfile
import logging
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta

from fastapi import HTTPException
from fastapi.responses import FileResponse

# 로깅 설정
logger = logging.getLogger(__name__)


class FileGeneratorError(Exception):
    """파일 생성 관련 오류"""
    pass


@dataclass
class GeneratedFile:
    """생성된 파일 정보"""
    filename: str
    file_path: Path
    file_size: int
    mime_type: str
    process_id: str
    created_at: float

    def __post_init__(self):
        """초기화 후 검증"""
        if self.file_size < 0:
            raise ValueError("File size must be non-negative")
        if not self.filename:
            raise ValueError("Filename cannot be empty")


@dataclass
class DownloadInfo:
    """다운로드 정보"""
    process_id: str
    filename: str
    file_size: int
    created_at: float
    is_ready: bool
    download_url: Optional[str] = None
    expires_at: Optional[float] = None


class FileGenerator:
    """파일 생성 및 다운로드 관리 클래스"""

    def __init__(self, temp_dir: Optional[str] = None):
        """
        FileGenerator 초기화

        Args:
            temp_dir: 임시 파일 저장 디렉토리 (None이면 시스템 기본값)
        """
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="ocr_files_"))

        # 디렉토리 생성
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 생성된 파일 추적
        self.generated_files: Dict[str, GeneratedFile] = {}

        logger.info(f"FileGenerator initialized with temp_dir: {self.temp_dir}")

    def generate_text_file(self,
                          text: str,
                          filename: str,
                          process_id: str,
                          encoding: str = 'utf-8') -> GeneratedFile:
        """
        텍스트 파일 생성

        Args:
            text: 저장할 텍스트 내용
            filename: 파일명
            process_id: 프로세스 ID
            encoding: 파일 인코딩 (기본: utf-8)

        Returns:
            GeneratedFile: 생성된 파일 정보

        Raises:
            FileGeneratorError: 파일 생성 실패 시
        """
        try:
            # 안전한 파일명으로 변환
            safe_filename = self._sanitize_filename(filename)

            # 파일 경로 생성
            file_path = self.temp_dir / safe_filename

            # 텍스트 파일 생성
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(text)

            # 파일 크기 계산
            file_size = file_path.stat().st_size

            # 파일 정보 생성
            generated_file = GeneratedFile(
                filename=safe_filename,
                file_path=file_path,
                file_size=file_size,
                mime_type="text/plain",
                process_id=process_id,
                created_at=time.time()
            )

            # 추적 목록에 추가 (기존 파일 덮어쓰기)
            self.generated_files[process_id] = generated_file

            logger.info(f"Text file generated: {safe_filename} ({file_size} bytes) for process {process_id}")
            return generated_file

        except Exception as e:
            logger.error(f"Failed to generate text file: {e}")
            raise FileGeneratorError(f"Failed to generate text file: {e}")

    def create_download_response(self,
                               process_id: str,
                               download_filename: Optional[str] = None) -> FileResponse:
        """
        다운로드 응답 생성

        Args:
            process_id: 프로세스 ID
            download_filename: 다운로드 시 사용할 파일명 (None이면 원본 파일명)

        Returns:
            FileResponse: FastAPI 파일 응답

        Raises:
            HTTPException: 파일을 찾을 수 없는 경우
        """
        if process_id not in self.generated_files:
            logger.warning(f"Download requested for non-existent process: {process_id}")
            raise HTTPException(
                status_code=404,
                detail=f"File for process '{process_id}' not found"
            )

        generated_file = self.generated_files[process_id]

        # 파일이 실제로 존재하는지 확인
        if not generated_file.file_path.exists():
            logger.error(f"File path does not exist: {generated_file.file_path}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found on disk for process '{process_id}'"
            )

        # 다운로드 파일명 결정
        final_filename = download_filename or generated_file.filename

        # FileResponse 생성
        response = FileResponse(
            path=str(generated_file.file_path),
            filename=final_filename,
            media_type=generated_file.mime_type,
            headers={
                "Content-Disposition": f"attachment; filename={final_filename}",
                "Content-Length": str(generated_file.file_size)
            }
        )

        logger.info(f"Download response created for process {process_id}: {final_filename}")
        return response

    def get_file_download_url(self, process_id: str) -> str:
        """
        파일 다운로드 URL 생성

        Args:
            process_id: 프로세스 ID

        Returns:
            str: 다운로드 URL

        Raises:
            FileGeneratorError: 파일을 찾을 수 없는 경우
        """
        if process_id not in self.generated_files:
            raise FileGeneratorError(f"File for process '{process_id}' not found")

        # 다운로드 URL 생성 (실제 웹 서버의 URL 구조에 맞춰 조정 필요)
        download_url = f"/api/download/{process_id}"

        return download_url

    def get_download_info(self, process_id: str) -> DownloadInfo:
        """
        다운로드 정보 조회

        Args:
            process_id: 프로세스 ID

        Returns:
            DownloadInfo: 다운로드 정보

        Raises:
            FileGeneratorError: 파일을 찾을 수 없는 경우
        """
        if process_id not in self.generated_files:
            raise FileGeneratorError(f"File for process '{process_id}' not found")

        generated_file = self.generated_files[process_id]

        # 파일 준비 상태 확인
        is_ready = generated_file.file_path.exists()

        # 다운로드 URL 생성
        download_url = None
        if is_ready:
            download_url = self.get_file_download_url(process_id)

        # 만료 시간 계산 (24시간 후)
        expires_at = generated_file.created_at + 24 * 3600

        return DownloadInfo(
            process_id=process_id,
            filename=generated_file.filename,
            file_size=generated_file.file_size,
            created_at=generated_file.created_at,
            is_ready=is_ready,
            download_url=download_url,
            expires_at=expires_at
        )

    def cleanup_temp_files(self, process_id: str) -> List[str]:
        """
        특정 프로세스의 임시 파일 정리

        Args:
            process_id: 정리할 프로세스 ID

        Returns:
            List[str]: 정리된 파일 경로 목록
        """
        cleaned_files = []

        if process_id in self.generated_files:
            generated_file = self.generated_files[process_id]

            try:
                if generated_file.file_path.exists():
                    generated_file.file_path.unlink()
                    cleaned_files.append(str(generated_file.file_path))
                    logger.info(f"Cleaned temp file: {generated_file.file_path}")

                # 추적 목록에서 제거
                del self.generated_files[process_id]

            except Exception as e:
                logger.error(f"Failed to clean temp file {generated_file.file_path}: {e}")

        return cleaned_files

    def cleanup_all_temp_files(self) -> int:
        """
        모든 임시 파일 정리

        Returns:
            int: 정리된 파일 수
        """
        cleaned_count = 0

        # 추적된 파일들 정리
        process_ids = list(self.generated_files.keys())
        for process_id in process_ids:
            cleaned_files = self.cleanup_temp_files(process_id)
            cleaned_count += len(cleaned_files)

        # 디렉토리 내 남은 파일들 정리
        try:
            if self.temp_dir.exists():
                for file_path in self.temp_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"Cleaned remaining file: {file_path}")

                # 빈 디렉토리 제거
                if not any(self.temp_dir.iterdir()):
                    self.temp_dir.rmdir()
                    logger.info(f"Removed empty temp directory: {self.temp_dir}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        logger.info(f"Cleaned up {cleaned_count} temporary files")
        return cleaned_count

    def cleanup_expired_files(self, max_age_seconds: int = 24 * 3600) -> List[str]:
        """
        만료된 임시 파일 정리

        Args:
            max_age_seconds: 최대 보관 시간 (초, 기본: 24시간)

        Returns:
            List[str]: 정리된 파일 경로 목록
        """
        current_time = time.time()
        expired_process_ids = []

        # 만료된 파일 찾기
        for process_id, generated_file in self.generated_files.items():
            if current_time - generated_file.created_at > max_age_seconds:
                expired_process_ids.append(process_id)

        # 만료된 파일 정리
        cleaned_files = []
        for process_id in expired_process_ids:
            cleaned = self.cleanup_temp_files(process_id)
            cleaned_files.extend(cleaned)

        if cleaned_files:
            logger.info(f"Cleaned {len(cleaned_files)} expired files")

        return cleaned_files

    def file_exists(self, process_id: str) -> bool:
        """
        파일 존재 여부 확인

        Args:
            process_id: 프로세스 ID

        Returns:
            bool: 파일 존재 여부
        """
        if process_id not in self.generated_files:
            return False

        generated_file = self.generated_files[process_id]
        return generated_file.file_path.exists()

    def get_all_generated_files(self) -> Dict[str, GeneratedFile]:
        """
        생성된 모든 파일 정보 조회

        Returns:
            Dict[str, GeneratedFile]: 프로세스 ID별 파일 정보
        """
        return self.generated_files.copy()

    def get_file_stats(self) -> Dict[str, Any]:
        """
        파일 통계 정보 조회

        Returns:
            Dict[str, Any]: 통계 정보
        """
        total_files = len(self.generated_files)
        total_size = sum(f.file_size for f in self.generated_files.values())

        # 실제 존재하는 파일 수 확인
        existing_files = sum(1 for f in self.generated_files.values() if f.file_path.exists())

        return {
            "total_files": total_files,
            "existing_files": existing_files,
            "total_size": total_size,
            "temp_dir": str(self.temp_dir),
            "oldest_file": min((f.created_at for f in self.generated_files.values()), default=None),
            "newest_file": max((f.created_at for f in self.generated_files.values()), default=None)
        }

    def _sanitize_filename(self, filename: str) -> str:
        """
        안전한 파일명으로 변환

        Args:
            filename: 원본 파일명

        Returns:
            str: 안전한 파일명
        """
        # 위험한 문자 제거
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

        # 연속된 점과 공백 정리
        safe_filename = re.sub(r'\.{2,}', '.', safe_filename)
        safe_filename = re.sub(r'\s+', ' ', safe_filename).strip()

        # 예약된 이름 처리 (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        name_without_ext = Path(safe_filename).stem
        if name_without_ext.upper() in reserved_names:
            safe_filename = f"file_{safe_filename}"

        # 빈 파일명 처리
        if not safe_filename or safe_filename == '.':
            safe_filename = f"file_{int(time.time())}.txt"

        # 파일명 길이 제한 (255자)
        if len(safe_filename) > 255:
            name = Path(safe_filename).stem[:240]
            ext = Path(safe_filename).suffix[:14]
            safe_filename = f"{name}{ext}"

        return safe_filename

    def __del__(self):
        """소멸자: 리소스 정리"""
        try:
            # 남은 임시 파일들 정리하지 않음 (명시적으로 cleanup 호출 필요)
            pass
        except:
            pass