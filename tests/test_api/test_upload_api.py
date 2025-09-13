"""
Upload API 테스트 모듈

이 모듈은 파일 업로드 API 엔드포인트를 테스트합니다:
- 파일 업로드 엔드포인트 테스트
- 업로드 상태 확인 테스트
- 파일 검증 테스트
- 에러 처리 테스트
"""

import pytest
import tempfile
import io
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.testclient import TestClient
from typing import Dict, Any

# Import from actual modules
from backend.api.upload import router as upload_router
from backend.utils.temp_storage import TempStorage


# FastAPI 테스트 앱 생성
app = FastAPI()
app.include_router(upload_router, prefix="/api")


@pytest.fixture
def client():
    """테스트 클라이언트 생성"""
    return TestClient(app)


@pytest.fixture
def temp_storage():
    """임시 저장소 Mock"""
    with patch('backend.api.upload.temp_storage') as mock_storage:
        mock_storage.save_file = Mock()  # sync Mock으로 변경
        mock_storage.get_file = Mock()
        mock_storage.file_exists = Mock()
        mock_storage.generate_file_id = Mock(return_value="test_id_123")
        mock_storage.cleanup_expired_files = Mock(return_value=[])
        mock_storage.get_storage_usage = Mock()
        mock_storage.delete_file = Mock(return_value=True)
        yield mock_storage


@pytest.fixture
def sample_pdf_file():
    """테스트용 PDF 파일 데이터"""
    # 간단한 PDF 헤더
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"
    return io.BytesIO(pdf_content)


@pytest.fixture
def invalid_file():
    """잘못된 파일 데이터"""
    return io.BytesIO(b"This is not a PDF file")


class TestUploadEndpoint:
    """파일 업로드 엔드포인트 테스트"""

    def test_upload_valid_pdf_success(self, client, temp_storage, sample_pdf_file):
        """유효한 PDF 업로드 성공 테스트"""
        # Mock 설정
        temp_storage.save_file.return_value = "test_upload_123"

        # 파일 업로드 요청
        files = {"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        # 응답 검증
        assert response.status_code == 200
        data = response.json()

        assert "upload_id" in data
        assert "filename" in data
        assert "file_size" in data
        assert "upload_time" in data
        assert data["filename"] == "test.pdf"
        assert data["file_size"] > 0

        # Mock 호출 검증
        temp_storage.save_file.assert_called_once()

    def test_upload_multiple_files_rejected(self, client, sample_pdf_file):
        """여러 파일 업로드 거부 테스트"""
        files = [
            ("file", ("test1.pdf", sample_pdf_file, "application/pdf")),
            ("file", ("test2.pdf", sample_pdf_file, "application/pdf"))
        ]
        response = client.post("/api/upload", files=files)

        assert response.status_code == 400
        assert "single file" in response.json()["detail"].lower()

    def test_upload_no_file_rejected(self, client):
        """파일 없는 업로드 거부 테스트"""
        response = client.post("/api/upload")

        assert response.status_code == 422  # FastAPI validation error

    def test_upload_empty_file_rejected(self, client):
        """빈 파일 업로드 거부 테스트"""
        empty_file = io.BytesIO(b"")
        files = {"file": ("empty.pdf", empty_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_invalid_file_type_rejected(self, client, invalid_file):
        """잘못된 파일 형식 거부 테스트"""
        files = {"file": ("test.txt", invalid_file, "text/plain")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()

    def test_upload_oversized_file_rejected(self, client):
        """크기 초과 파일 거부 테스트"""
        # 50MB 초과 파일 시뮬레이션
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        large_file = io.BytesIO(large_content)

        files = {"file": ("large.pdf", large_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 413  # Request Entity Too Large

    def test_upload_invalid_filename_sanitized(self, client, temp_storage, sample_pdf_file):
        """잘못된 파일명 정리 테스트"""
        temp_storage.save_file.return_value = "test_upload_123"

        # 위험한 문자가 포함된 파일명
        files = {"file": ("../../../etc/passwd.pdf", sample_pdf_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()

        # 파일명이 안전하게 정리되었는지 확인
        assert "../" not in data["filename"]
        assert data["filename"].endswith(".pdf")
        # 위험한 경로 순회 문자가 변환되었는지 확인
        assert not data["filename"].startswith("../")
        assert not data["filename"].startswith("/")
        print(f"Sanitized filename: {data['filename']}")  # 디버깅용

    def test_upload_pdf_validation_success(self, client, temp_storage):
        """PDF 파일 검증 성공 테스트"""
        temp_storage.save_file.return_value = "test_upload_123"

        # 실제 PDF 헤더를 포함한 파일
        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n174\n%%EOF"
        pdf_file = io.BytesIO(pdf_content)

        files = {"file": ("valid.pdf", pdf_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 200

    def test_upload_corrupted_pdf_rejected(self, client):
        """손상된 PDF 파일 거부 테스트"""
        # PDF 헤더만 있고 내용이 잘못된 파일
        corrupted_pdf = io.BytesIO(b"%PDF-1.4\nThis is corrupted content")

        files = {"file": ("corrupted.pdf", corrupted_pdf, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower() or "corrupted" in response.json()["detail"].lower()

    def test_upload_storage_error_handling(self, client, temp_storage, sample_pdf_file):
        """저장소 오류 처리 테스트"""
        # 저장소 오류 시뮬레이션
        temp_storage.save_file.side_effect = Exception("Storage full")

        files = {"file": ("test.pdf", sample_pdf_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 500
        assert "storage" in response.json()["detail"].lower()


class TestUploadStatus:
    """업로드 상태 확인 테스트"""

    def test_get_upload_status_success(self, client, temp_storage):
        """업로드 상태 조회 성공 테스트"""
        from backend.utils.temp_storage import FileInfo
        from datetime import datetime

        # Mock 설정
        mock_file_info = FileInfo(
            content=b"test",
            filename="test.pdf",
            uploader_id="web_user",
            created_at=datetime.fromisoformat("2024-01-01T00:00:00"),
            file_size=1024
        )
        temp_storage.get_file.return_value = mock_file_info

        response = client.get("/api/upload/test_upload_123/status")

        assert response.status_code == 200
        data = response.json()

        assert data["upload_id"] == "test_upload_123"
        assert data["filename"] == "test.pdf"
        assert data["status"] == "uploaded"
        assert data["file_size"] == 1024

    def test_get_upload_status_not_found(self, client, temp_storage):
        """존재하지 않는 업로드 상태 조회 테스트"""
        temp_storage.get_file.return_value = None

        response = client.get("/api/upload/nonexistent_id/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_upload_status_invalid_id(self, client, temp_storage):
        """잘못된 업로드 ID로 상태 조회 테스트"""
        temp_storage.get_file.return_value = None
        response = client.get("/api/upload/invalid-id-format/status")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_upload_list_success(self, client, temp_storage):
        """업로드 목록 조회 성공 테스트"""
        # 현재 API는 빈 목록을 반환하도록 구현되어 있음
        response = client.get("/api/upload/list")

        assert response.status_code == 200
        data = response.json()

        assert data["uploads"] == []
        assert data["total"] == 0

    def test_get_upload_list_empty(self, client, temp_storage):
        """빈 업로드 목록 조회 테스트"""
        response = client.get("/api/upload/list")

        assert response.status_code == 200
        data = response.json()

        assert data["uploads"] == []
        assert data["total"] == 0


class TestFileValidation:
    """파일 검증 테스트"""

    def test_validate_pdf_mime_type_success(self, client, sample_pdf_file):
        """PDF MIME 타입 검증 성공 테스트"""
        with patch('backend.api.upload.temp_storage.save_file') as mock_save:
            mock_save.return_value = "test_upload_123"

            files = {"file": ("test.pdf", sample_pdf_file, "application/pdf")}
            response = client.post("/api/upload", files=files)

            assert response.status_code == 200

    def test_validate_pdf_mime_type_failure(self, client, invalid_file):
        """PDF MIME 타입 검증 실패 테스트"""
        files = {"file": ("test.jpg", invalid_file, "image/jpeg")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 400

    def test_validate_pdf_content_success(self, client):
        """PDF 내용 검증 성공 테스트"""
        # 유효한 PDF 내용
        valid_pdf = io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<</Root 1 0 R>>\n%%EOF")

        with patch('backend.api.upload.temp_storage.save_file') as mock_save:
            mock_save.return_value = "test_upload_123"

            files = {"file": ("valid.pdf", valid_pdf, "application/pdf")}
            response = client.post("/api/upload", files=files)

            assert response.status_code == 200

    def test_validate_pdf_content_failure(self, client, invalid_file):
        """PDF 내용 검증 실패 테스트"""
        files = {"file": ("fake.pdf", invalid_file, "application/pdf")}
        response = client.post("/api/upload", files=files)

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()

    def test_validate_file_size_within_limit(self, client, sample_pdf_file):
        """파일 크기 제한 내 검증 테스트"""
        with patch('backend.api.upload.temp_storage.save_file') as mock_save:
            mock_save.return_value = "test_upload_123"

            files = {"file": ("small.pdf", sample_pdf_file, "application/pdf")}
            response = client.post("/api/upload", files=files)

            assert response.status_code == 200

    def test_validate_filename_length_limit(self, client, sample_pdf_file):
        """파일명 길이 제한 테스트"""
        with patch('backend.api.upload.temp_storage.save_file') as mock_save:
            mock_save.return_value = "test_upload_123"

            # 매우 긴 파일명 (255자 초과)
            long_name = "a" * 250 + ".pdf"
            files = {"file": (long_name, sample_pdf_file, "application/pdf")}
            response = client.post("/api/upload", files=files)

            assert response.status_code == 200
            # 파일명이 적절히 잘렸는지 확인
            data = response.json()
            assert len(data["filename"]) <= 255


class TestRateLimiting:
    """속도 제한 테스트"""

    def test_upload_rate_limiting(self, client, sample_pdf_file):
        """업로드 속도 제한 테스트"""
        with patch('backend.api.upload.temp_storage.save_file') as mock_save, \
             patch('backend.api.upload.check_rate_limit') as mock_rate_limit:

            mock_save.return_value = "test_upload_123"

            # 처음 몇 번은 성공하도록 하고, 나중에는 제한
            def side_effect_rate_limit():
                if mock_rate_limit.call_count > 3:
                    raise HTTPException(status_code=429, detail="Rate limited")

            mock_rate_limit.side_effect = side_effect_rate_limit

            # 연속으로 여러 번 업로드 시도
            files = {"file": ("test.pdf", sample_pdf_file, "application/pdf")}

            responses = []
            for i in range(6):  # 6회 연속 업로드
                sample_pdf_file.seek(0)  # 파일 포인터 리셋
                response = client.post("/api/upload", files=files)
                responses.append(response.status_code)

            # 일부 요청은 속도 제한으로 거부되어야 함
            success_count = sum(1 for status in responses if status == 200)
            rate_limited_count = sum(1 for status in responses if status == 429)

            # 적어도 일부 요청은 성공해야 하고, 일부는 제한되어야 함
            assert success_count > 0
            assert rate_limited_count > 0

    def test_concurrent_uploads_handling(self, client, sample_pdf_file):
        """동시 업로드 처리 테스트"""
        # 이 테스트는 실제 구현에서 동시성 처리를 확인
        # 현재는 기본 구조만 테스트
        with patch('backend.api.upload.temp_storage.save_file') as mock_save:
            mock_save.return_value = "test_upload_123"

            files = {"file": ("test.pdf", sample_pdf_file, "application/pdf")}
            response = client.post("/api/upload", files=files)

            assert response.status_code == 200


class TestCleanupAndMaintenance:
    """정리 및 유지보수 테스트"""

    def test_expired_uploads_cleanup(self, client, temp_storage):
        """만료된 업로드 정리 테스트"""
        response = client.delete("/api/upload/cleanup/expired")

        assert response.status_code == 200
        data = response.json()
        assert "cleaned_count" in data

    def test_upload_statistics(self, client, temp_storage):
        """업로드 통계 조회 테스트"""
        from backend.utils.temp_storage import StorageUsage

        # Mock 설정
        mock_usage = StorageUsage(
            total_files=100,
            total_size=1024 * 1024 * 1024,  # 1GB
            files_by_user={"web_user": 100}
        )
        temp_storage.get_storage_usage.return_value = mock_usage

        response = client.get("/api/upload/statistics")

        assert response.status_code == 200
        data = response.json()

        assert data["total_uploads"] == 100
        assert data["total_size"] == 1024 * 1024 * 1024
        assert data["success_rate"] == 1.0

    def test_health_check(self, client):
        """업로드 서비스 헬스체크 테스트"""
        response = client.get("/api/upload/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "storage" in data
        assert "timestamp" in data