"""
Download API 테스트 모듈

이 모듈은 파일 다운로드 API 엔드포인트를 테스트합니다:
- 파일 다운로드 테스트
- 권한 확인 테스트
- 파일 만료 처리 테스트
- 임시 파일 정리 테스트
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Import from actual modules
from backend.api.download import router as download_router


# FastAPI 테스트 앱 생성
app = FastAPI()
app.include_router(download_router, prefix="/api")


@pytest.fixture
def client():
    """테스트 클라이언트 생성"""
    return TestClient(app)


@pytest.fixture
def temp_storage():
    """임시 저장소 Mock"""
    with patch('backend.api.download.temp_storage') as mock_storage:
        mock_storage.get_file = Mock()
        mock_storage.delete_file = Mock()
        mock_storage.file_exists = Mock(return_value=True)
        mock_storage.get_storage_usage = Mock()
        yield mock_storage


@pytest.fixture
def file_generator():
    """파일 생성기 Mock"""
    with patch('backend.api.download.file_generator') as mock_generator:
        mock_generator.create_download_response = Mock()
        mock_generator.cleanup_temp_files = Mock()
        mock_generator.get_file_download_url = Mock()
        yield mock_generator


@pytest.fixture
def sample_file():
    """테스트용 임시 파일 생성"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Sample OCR result text\n한글 텍스트 테스트")
        temp_path = f.name

    yield temp_path

    # 정리
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestFileDownload:
    """파일 다운로드 테스트"""

    def test_download_file_success(self, client, file_generator, sample_file):
        """파일 다운로드 성공 테스트"""
        # Mock 설정
        mock_response = FileResponse(
            path=sample_file,
            filename="result.txt",
            media_type="text/plain; charset=utf-8"
        )
        file_generator.create_download_response.return_value = mock_response

        response = client.get("/api/download/proc_123")

        assert response.status_code == 200
        assert "content-disposition" in response.headers
        file_generator.create_download_response.assert_called_once_with("proc_123")

    def test_download_file_not_found(self, client, file_generator):
        """존재하지 않는 파일 다운로드 테스트"""
        file_generator.create_download_response.side_effect = FileNotFoundError("File not found")

        response = client.get("/api/download/nonexistent_process")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_download_invalid_process_id(self, client):
        """잘못된 프로세스 ID 테스트"""
        # 잘못된 형식의 프로세스 ID
        response = client.get("/api/download/invalid@id")

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_download_expired_file(self, client, file_generator):
        """만료된 파일 다운로드 테스트"""
        file_generator.create_download_response.side_effect = HTTPException(
            status_code=410,
            detail="File has expired and is no longer available"
        )

        response = client.get("/api/download/expired_process_123")

        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()

    def test_download_file_access_denied(self, client, file_generator):
        """파일 접근 권한 없음 테스트"""
        file_generator.create_download_response.side_effect = HTTPException(
            status_code=403,
            detail="Access denied"
        )

        response = client.get("/api/download/forbidden_process")

        assert response.status_code == 403
        assert "access denied" in response.json()["detail"].lower()

    def test_download_with_custom_filename(self, client, file_generator, sample_file):
        """사용자 정의 파일명으로 다운로드 테스트"""
        mock_response = FileResponse(
            path=sample_file,
            filename="custom_name.txt",
            media_type="text/plain; charset=utf-8"
        )
        file_generator.create_download_response.return_value = mock_response

        response = client.get("/api/download/proc_123?filename=custom_name.txt")

        assert response.status_code == 200
        file_generator.create_download_response.assert_called_once()


class TestFileCleanup:
    """파일 정리 테스트"""

    def test_delete_file_success(self, client, file_generator):
        """파일 삭제 성공 테스트"""
        file_generator.cleanup_temp_files.return_value = ["file1.txt", "file2.txt"]

        response = client.delete("/api/download/proc_123")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Files deleted successfully"
        assert data["process_id"] == "proc_123"
        assert data["deleted_files"] == ["file1.txt", "file2.txt"]

    def test_delete_file_not_found(self, client, file_generator):
        """존재하지 않는 파일 삭제 테스트"""
        file_generator.cleanup_temp_files.side_effect = FileNotFoundError("Process not found")

        response = client.delete("/api/download/nonexistent_process")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_file_already_deleted(self, client, file_generator):
        """이미 삭제된 파일 삭제 시도 테스트"""
        file_generator.cleanup_temp_files.return_value = []

        response = client.delete("/api/download/already_deleted")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Files deleted successfully"
        assert data["deleted_files"] == []

    def test_cleanup_expired_files(self, client, file_generator):
        """만료된 파일 일괄 정리 테스트"""
        file_generator.cleanup_temp_files.return_value = [
            "expired_file1.txt", "expired_file2.txt"
        ]

        response = client.delete("/api/download/cleanup/expired?max_age_hours=24")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "cleaned_count" in data


class TestPermissionChecks:
    """권한 확인 테스트"""

    def test_download_with_valid_user(self, client, file_generator, sample_file):
        """유효한 사용자 파일 다운로드 테스트"""
        # Mock 설정: 사용자 검증 통과
        mock_response = FileResponse(
            path=sample_file,
            filename="authorized_file.txt",
            media_type="text/plain; charset=utf-8"
        )
        file_generator.create_download_response.return_value = mock_response

        response = client.get("/api/download/user_proc_123?user_id=user_456")

        assert response.status_code == 200

    def test_download_with_invalid_user(self, client, file_generator):
        """잘못된 사용자 파일 다운로드 테스트"""
        file_generator.create_download_response.side_effect = HTTPException(
            status_code=403,
            detail="Access denied. File belongs to different user."
        )

        response = client.get("/api/download/other_user_proc?user_id=wrong_user")

        assert response.status_code == 403

    def test_download_without_user_id(self, client, file_generator, sample_file):
        """사용자 ID 없이 다운로드 테스트 (게스트 접근)"""
        # 게스트는 제한된 접근만 허용
        mock_response = FileResponse(
            path=sample_file,
            filename="guest_file.txt",
            media_type="text/plain; charset=utf-8"
        )
        file_generator.create_download_response.return_value = mock_response

        response = client.get("/api/download/public_proc_123")

        assert response.status_code == 200


class TestFileMetadata:
    """파일 메타데이터 테스트"""

    def test_get_download_info_success(self, client):
        """다운로드 정보 조회 성공 테스트"""
        with patch('backend.api.download.get_download_info') as mock_info:
            mock_info.return_value = {
                "process_id": "proc_123",
                "filename": "result.txt",
                "file_size": 2048,
                "created_at": "2025-01-13T10:00:00Z",
                "expires_at": "2025-01-14T10:00:00Z",
                "download_count": 1,
                "is_available": True
            }

            response = client.get("/api/download/proc_123/info")

            assert response.status_code == 200
            data = response.json()
            assert data["process_id"] == "proc_123"
            assert data["filename"] == "result.txt"
            assert data["is_available"] == True

    def test_get_download_info_not_found(self, client):
        """존재하지 않는 파일 정보 조회 테스트"""
        with patch('backend.api.download.get_download_info') as mock_info:
            mock_info.return_value = None

            response = client.get("/api/download/nonexistent/info")

            assert response.status_code == 404


class TestDownloadStatistics:
    """다운로드 통계 테스트"""

    def test_get_download_statistics(self, client):
        """다운로드 통계 조회 테스트"""
        with patch('backend.api.download.get_download_statistics') as mock_stats:
            mock_stats.return_value = {
                "total_downloads": 150,
                "active_files": 25,
                "expired_files": 5,
                "total_file_size": 1048576,  # 1MB
                "average_file_size": 6990,
                "most_downloaded_files": [
                    {"process_id": "proc_123", "downloads": 15},
                    {"process_id": "proc_456", "downloads": 12}
                ]
            }

            response = client.get("/api/download-stats/statistics")

            assert response.status_code == 200
            data = response.json()
            assert data["total_downloads"] == 150
            assert data["active_files"] == 25
            assert len(data["most_downloaded_files"]) == 2

    def test_get_download_usage(self, client, temp_storage):
        """다운로드 사용량 조회 테스트"""
        temp_storage.get_storage_usage.return_value = Mock(
            total_files=50,
            total_size=2097152,  # 2MB
            available_space=52428800  # 50MB
        )

        response = client.get("/api/download-stats/usage")

        assert response.status_code == 200
        data = response.json()
        assert "total_files" in data
        assert "total_size" in data


class TestErrorHandling:
    """오류 처리 테스트"""

    def test_download_server_error(self, client, file_generator):
        """서버 오류 처리 테스트"""
        file_generator.create_download_response.side_effect = Exception("Database connection failed")

        response = client.get("/api/download/proc_123")

        assert response.status_code == 500
        assert "internal server error" in response.json()["detail"].lower()

    def test_download_rate_limiting(self, client):
        """다운로드 속도 제한 테스트"""
        with patch('backend.api.download.check_download_rate_limit') as mock_limit:
            mock_limit.side_effect = HTTPException(
                status_code=429,
                detail="Too many download requests. Please try again later."
            )

            response = client.get("/api/download/proc_123")

            assert response.status_code == 429
            assert "too many" in response.json()["detail"].lower()

    def test_download_maintenance_mode(self, client):
        """유지보수 모드 테스트"""
        with patch('backend.api.download.is_maintenance_mode', return_value=True):
            response = client.get("/api/download/proc_123")

            assert response.status_code == 503
            assert "maintenance" in response.json()["detail"].lower()


class TestSecurityFeatures:
    """보안 기능 테스트"""

    def test_download_with_token_validation(self, client, file_generator, sample_file):
        """토큰 검증 다운로드 테스트"""
        mock_response = FileResponse(
            path=sample_file,
            filename="secure_file.txt",
            media_type="text/plain; charset=utf-8"
        )
        file_generator.create_download_response.return_value = mock_response

        # 유효한 토큰으로 요청
        headers = {"Authorization": "Bearer valid_token_123"}
        response = client.get("/api/download/secure_proc_123", headers=headers)

        assert response.status_code == 200

    def test_download_with_invalid_token(self, client):
        """잘못된 토큰으로 다운로드 테스트"""
        with patch('backend.api.download.validate_download_token') as mock_validate:
            mock_validate.side_effect = HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/api/download/secure_proc_123", headers=headers)

            assert response.status_code == 401

    def test_download_ip_whitelist_check(self, client, file_generator, sample_file):
        """IP 화이트리스트 확인 테스트"""
        # Mock 설정: IP가 허용 목록에 있음
        mock_response = FileResponse(
            path=sample_file,
            filename="whitelist_file.txt",
            media_type="text/plain; charset=utf-8"
        )
        file_generator.create_download_response.return_value = mock_response

        with patch('backend.api.download.is_ip_allowed', return_value=True):
            response = client.get("/api/download/proc_123")
            assert response.status_code == 200

    def test_download_ip_blocked(self, client):
        """차단된 IP 다운로드 시도 테스트"""
        with patch('backend.api.download.is_ip_allowed', return_value=False):
            response = client.get("/api/download/proc_123")
            assert response.status_code == 403