"""
Processing API 테스트 모듈

이 모듈은 문서 처리 API 엔드포인트를 테스트합니다:
- 처리 시작 엔드포인트 테스트
- 처리 상태 확인 테스트
- 설정 변경 테스트
- 비동기 작업 처리 테스트
- 오류 시나리오 테스트
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from typing import Dict, Any, Optional
from datetime import datetime

# Import from actual modules
from backend.api.processing import router as processing_router


# FastAPI 테스트 앱 생성
app = FastAPI()
app.include_router(processing_router, prefix="/api")


@pytest.fixture
def client():
    """테스트 클라이언트 생성"""
    return TestClient(app)


@pytest.fixture
def temp_storage():
    """임시 저장소 Mock"""
    with patch('backend.api.processing.temp_storage') as mock_storage:
        mock_storage.get_file = Mock()
        mock_storage.file_exists = Mock(return_value=True)
        yield mock_storage


@pytest.fixture
def celery_app():
    """Celery 앱 Mock"""
    with patch('backend.api.processing.celery_app') as mock_celery:
        yield mock_celery


@pytest.fixture
def processing_task():
    """처리 태스크 Mock"""
    with patch('backend.api.processing.process_document') as mock_task:
        mock_result = Mock()
        mock_result.id = "task_123"
        mock_result.status = "PENDING"
        mock_result.result = None
        mock_task.delay.return_value = mock_result
        yield mock_task


class TestProcessingStart:
    """처리 시작 엔드포인트 테스트"""

    def test_start_processing_success(self, client, temp_storage, processing_task):
        """문서 처리 시작 성공 테스트"""
        # Mock 설정
        temp_storage.file_exists.return_value = True

        request_data = {
            "preprocessing_options": {
                "apply_clahe": True,
                "deskew_enabled": True,
                "noise_removal": True,
                "adaptive_threshold": True
            },
            "ocr_engine": "paddle",
            "correction_enabled": True
        }

        response = client.post("/api/process/test_upload_123", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "process_id" in data
        assert data["upload_id"] == "test_upload_123"
        assert data["status"] == "started"
        assert "estimated_time" in data

        # Mock 호출 검증
        processing_task.delay.assert_called_once()

    def test_start_processing_file_not_found(self, client, temp_storage):
        """존재하지 않는 파일 처리 시작 테스트"""
        temp_storage.file_exists.return_value = False

        request_data = {
            "preprocessing_options": {
                "apply_clahe": True
            },
            "ocr_engine": "paddle"
        }

        response = client.post("/api/process/nonexistent_upload", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_start_processing_invalid_ocr_engine(self, client, temp_storage):
        """잘못된 OCR 엔진 지정 테스트"""
        temp_storage.file_exists.return_value = True

        request_data = {
            "ocr_engine": "invalid_engine",
            "correction_enabled": False
        }

        response = client.post("/api/process/test_upload_123", json=request_data)

        assert response.status_code == 422
        # Check if it's a validation error
        data = response.json()
        assert "detail" in data

    def test_start_processing_default_options(self, client, temp_storage, processing_task):
        """기본 옵션으로 처리 시작 테스트"""
        temp_storage.file_exists.return_value = True

        # 최소한의 옵션만 제공
        request_data = {
            "ocr_engine": "paddle"
        }

        response = client.post("/api/process/test_upload_123", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "started"
        processing_task.delay.assert_called_once()

    def test_start_processing_duplicate_request(self, client, temp_storage, processing_task):
        """중복 처리 요청 테스트"""
        temp_storage.file_exists.return_value = True

        request_data = {
            "ocr_engine": "paddle"
        }

        # 첫 번째 요청
        response1 = client.post("/api/process/test_upload_123", json=request_data)
        assert response1.status_code == 200

        # 같은 upload_id로 두 번째 요청
        with patch('backend.api.processing.get_processing_status') as mock_status:
            mock_status.return_value = {"status": "processing"}
            response2 = client.post("/api/process/test_upload_123", json=request_data)

            # 이미 처리 중인 경우 409 Conflict 또는 기존 상태 반환
            assert response2.status_code in [200, 409]

    def test_start_processing_custom_preprocessing(self, client, temp_storage, processing_task):
        """사용자 정의 전처리 옵션 테스트"""
        temp_storage.file_exists.return_value = True

        request_data = {
            "preprocessing_options": {
                "apply_clahe": False,
                "deskew_enabled": True,
                "noise_removal": False,
                "adaptive_threshold": True,
                "super_resolution": True  # 선택적 옵션
            },
            "ocr_engine": "tesseract",
            "correction_enabled": True,
            "correction_options": {
                "spacing_correction": True,
                "spelling_correction": False,
                "custom_rules": True
            }
        }

        response = client.post("/api/process/test_upload_123", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "started"

        # 전달된 옵션 검증
        call_args = processing_task.delay.call_args
        assert call_args is not None


class TestProcessingStatus:
    """처리 상태 확인 테스트"""

    def test_get_processing_status_pending(self, client):
        """대기 중 상태 조회 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "task_id": "task_123",
                "status": "PENDING",
                "progress": 0,
                "current_step": "Waiting to start",
                "result": None,
                "error": None
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["process_id"] == "task_123"
            assert data["status"] == "pending"
            assert data["progress"] == 0
            assert data["current_step"] == "Waiting to start"

    def test_get_processing_status_in_progress(self, client):
        """처리 중 상태 조회 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "task_id": "task_123",
                "status": "PROGRESS",
                "progress": 45,
                "current_step": "OCR processing",
                "result": None,
                "error": None,
                "estimated_time": 120
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "processing"
            assert data["progress"] == 45
            assert data["current_step"] == "OCR processing"
            assert data["estimated_time"] == 120

    def test_get_processing_status_completed(self, client):
        """완료 상태 조회 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "task_id": "task_123",
                "status": "SUCCESS",
                "progress": 100,
                "current_step": "Completed",
                "result": {
                    "output_file_id": "output_456",
                    "original_text": "원본 텍스트",
                    "corrected_text": "교정된 텍스트",
                    "processing_time": 95.5,
                    "statistics": {
                        "cer_score": 0.02,
                        "wer_score": 0.15,
                        "corrections_made": 5
                    }
                },
                "error": None
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "completed"
            assert data["progress"] == 100
            assert "result" in data
            assert data["result"]["output_file_id"] == "output_456"
            assert data["result"]["statistics"]["cer_score"] == 0.02

    def test_get_processing_status_failed(self, client):
        """실패 상태 조회 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "task_id": "task_123",
                "status": "FAILURE",
                "progress": 35,
                "current_step": "OCR processing failed",
                "result": None,
                "error": {
                    "error_type": "OCRError",
                    "message": "Failed to recognize text",
                    "details": "Image quality too low"
                }
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "failed"
            assert data["progress"] == 35
            assert "error" in data
            assert data["error"]["error_type"] == "OCRError"

    def test_get_processing_status_not_found(self, client):
        """존재하지 않는 프로세스 상태 조회 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = None

            response = client.get("/api/process/nonexistent_task/status")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_processing_history(self, client):
        """처리 히스토리 조회 테스트"""
        with patch('backend.api.processing.get_processing_history') as mock_history:
            mock_history.return_value = [
                {
                    "process_id": "task_123",
                    "upload_id": "upload_456",
                    "status": "completed",
                    "created_at": "2024-01-01T10:00:00Z",
                    "completed_at": "2024-01-01T10:02:30Z",
                    "processing_time": 150.0
                },
                {
                    "process_id": "task_124",
                    "upload_id": "upload_457",
                    "status": "failed",
                    "created_at": "2024-01-01T11:00:00Z",
                    "failed_at": "2024-01-01T11:01:15Z",
                    "error": "OCR failed"
                }
            ]

            response = client.get("/api/process/history")

            assert response.status_code == 200
            data = response.json()

            assert "history" in data
            assert len(data["history"]) == 2
            assert data["history"][0]["status"] == "completed"


class TestProcessingSettings:
    """처리 설정 테스트"""

    def test_update_processing_settings_success(self, client):
        """처리 설정 업데이트 성공 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status, \
             patch('backend.api.processing.update_task_settings') as mock_update:

            mock_status.return_value = {"status": "PROGRESS", "progress": 25}
            mock_update.return_value = True

            new_settings = {
                "ocr_engine": "tesseract",
                "correction_enabled": False,
                "preprocessing_options": {
                    "apply_clahe": False,
                    "noise_removal": True
                }
            }

            response = client.put("/api/process/task_123/settings", json=new_settings)

            assert response.status_code == 200
            data = response.json()

            assert data["message"] == "Settings updated successfully"
            mock_update.assert_called_once()
            # Check that the function was called with task_123 and some settings
            call_args = mock_update.call_args
            assert call_args[0][0] == "task_123"  # first argument
            # Check that key values are preserved
            settings_dict = call_args[0][1]
            assert settings_dict["ocr_engine"] == "tesseract"
            assert settings_dict["correction_enabled"] == False

    def test_update_processing_settings_completed_task(self, client):
        """완료된 작업의 설정 변경 시도 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {"status": "SUCCESS", "progress": 100}

            new_settings = {
                "ocr_engine": "tesseract"
            }

            response = client.put("/api/process/task_123/settings", json=new_settings)

            assert response.status_code == 400
            assert "cannot update" in response.json()["detail"].lower()

    def test_update_processing_settings_invalid_task(self, client):
        """존재하지 않는 작업의 설정 변경 시도 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = None

            new_settings = {
                "ocr_engine": "paddle"
            }

            response = client.put("/api/process/nonexistent/settings", json=new_settings)

            assert response.status_code == 404

    def test_get_processing_settings(self, client):
        """처리 설정 조회 테스트"""
        with patch('backend.api.processing.get_task_settings') as mock_settings:
            mock_settings.return_value = {
                "preprocessing_options": {
                    "apply_clahe": True,
                    "deskew_enabled": True,
                    "noise_removal": False,
                    "adaptive_threshold": True
                },
                "ocr_engine": "paddle",
                "correction_enabled": True,
                "correction_options": {
                    "spacing_correction": True,
                    "spelling_correction": True,
                    "custom_rules": False
                }
            }

            response = client.get("/api/process/task_123/settings")

            assert response.status_code == 200
            data = response.json()

            assert data["ocr_engine"] == "paddle"
            assert data["correction_enabled"] is True
            assert data["preprocessing_options"]["apply_clahe"] is True


class TestAsyncProcessing:
    """비동기 처리 테스트"""

    def test_cancel_processing_success(self, client):
        """처리 취소 성공 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status, \
             patch('backend.api.processing.cancel_task') as mock_cancel:

            mock_status.return_value = {"status": "PROGRESS", "progress": 30}
            mock_cancel.return_value = True

            response = client.delete("/api/process/task_123/cancel")

            assert response.status_code == 200
            data = response.json()

            assert data["message"] == "Processing cancelled successfully"
            assert data["process_id"] == "task_123"
            mock_cancel.assert_called_once_with("task_123")

    def test_cancel_processing_already_completed(self, client):
        """이미 완료된 처리 취소 시도 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {"status": "SUCCESS", "progress": 100}

            response = client.delete("/api/process/task_123/cancel")

            assert response.status_code == 400
            assert "already completed" in response.json()["detail"].lower()

    def test_restart_failed_processing(self, client, temp_storage, processing_task):
        """실패한 처리 재시작 테스트"""
        temp_storage.file_exists.return_value = True

        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {"status": "FAILURE", "progress": 45}

            response = client.post("/api/process/task_123/restart")

            assert response.status_code == 200
            data = response.json()

            assert data["message"] == "Processing restarted successfully"
            assert "new_process_id" in data

    def test_batch_processing_status(self, client):
        """배치 처리 상태 조회 테스트"""
        with patch('backend.api.processing.get_multiple_task_status') as mock_batch_status:
            mock_batch_status.return_value = {
                "task_123": {"status": "PROGRESS", "progress": 50},
                "task_124": {"status": "SUCCESS", "progress": 100},
                "task_125": {"status": "FAILURE", "progress": 25}
            }

            task_ids = ["task_123", "task_124", "task_125"]
            response = client.post("/api/process/batch/status", json={"task_ids": task_ids})

            assert response.status_code == 200
            data = response.json()

            assert "results" in data
            assert len(data["results"]) == 3
            assert data["results"]["task_123"]["status"] == "processing"
            assert data["results"]["task_124"]["status"] == "completed"
            assert data["results"]["task_125"]["status"] == "failed"


class TestErrorScenarios:
    """오류 시나리오 테스트"""

    def test_processing_timeout_handling(self, client, processing_task):
        """처리 타임아웃 처리 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "TIMEOUT",
                "progress": 80,
                "current_step": "Text correction timed out",
                "error": {"error_type": "TimeoutError", "message": "Processing exceeded time limit"}
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "failed"
            assert data["error"]["error_type"] == "TimeoutError"

    def test_processing_memory_error(self, client):
        """메모리 부족 오류 처리 테스트"""
        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "FAILURE",
                "progress": 65,
                "current_step": "Image processing failed",
                "error": {
                    "error_type": "MemoryError",
                    "message": "Not enough memory to process large image",
                    "suggestions": ["Try with smaller image", "Enable image compression"]
                }
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "failed"
            assert "suggestions" in data["error"]

    def test_processing_dependency_error(self, client, temp_storage):
        """의존성 오류 처리 테스트"""
        temp_storage.file_exists.return_value = True

        with patch('backend.api.processing.process_document') as mock_task:
            mock_task.delay.side_effect = Exception("Celery worker not available")

            request_data = {
                "ocr_engine": "paddle"
            }

            response = client.post("/api/process/test_upload_123", json=request_data)

            assert response.status_code == 500
            assert "internal server error" in response.json()["detail"].lower()

    def test_processing_invalid_file_format(self, client, temp_storage):
        """잘못된 파일 형식 처리 테스트"""
        temp_storage.file_exists.return_value = True

        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "FAILURE",
                "progress": 10,
                "current_step": "PDF validation failed",
                "error": {
                    "error_type": "InvalidFileError",
                    "message": "File is corrupted or not a valid PDF"
                }
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "failed"
            assert data["error"]["error_type"] == "InvalidFileError"

    def test_processing_ocr_engine_unavailable(self, client, temp_storage):
        """OCR 엔진 사용 불가 처리 테스트"""
        temp_storage.file_exists.return_value = True

        with patch('backend.api.processing.get_task_status') as mock_status:
            mock_status.return_value = {
                "status": "FAILURE",
                "progress": 40,
                "current_step": "OCR engine initialization failed",
                "error": {
                    "error_type": "OCREngineError",
                    "message": "PaddleOCR engine not available",
                    "fallback_suggestion": "Try using Tesseract engine"
                }
            }

            response = client.get("/api/process/task_123/status")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "failed"
            assert "fallback_suggestion" in data["error"]


class TestProcessingMetrics:
    """처리 메트릭 테스트"""

    def test_get_processing_metrics(self, client):
        """처리 메트릭 조회 테스트"""
        with patch('backend.api.processing.get_processing_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "total_processed": 150,
                "successful_count": 142,
                "failed_count": 8,
                "average_processing_time": 95.5,
                "success_rate": 0.947,
                "engine_usage": {
                    "paddle": 120,
                    "tesseract": 30
                },
                "common_errors": [
                    {"error_type": "LowImageQuality", "count": 5},
                    {"error_type": "MemoryError", "count": 2}
                ]
            }

            response = client.get("/api/process/metrics")

            assert response.status_code == 200
            data = response.json()

            assert data["total_processed"] == 150
            assert data["success_rate"] == 0.947
            assert "engine_usage" in data
            assert "common_errors" in data

    def test_get_processing_performance_stats(self, client):
        """처리 성능 통계 조회 테스트"""
        with patch('backend.api.processing.get_performance_stats') as mock_stats:
            mock_stats.return_value = {
                "last_24h": {
                    "total_tasks": 45,
                    "avg_processing_time": 87.2,
                    "peak_processing_hour": "14:00-15:00"
                },
                "last_7d": {
                    "total_tasks": 298,
                    "avg_processing_time": 91.8,
                    "busiest_day": "Monday"
                },
                "resource_usage": {
                    "avg_cpu_usage": 0.65,
                    "avg_memory_usage": 0.78,
                    "queue_length": 3
                }
            }

            response = client.get("/api/process/stats")

            assert response.status_code == 200
            data = response.json()

            assert "last_24h" in data
            assert "resource_usage" in data
            assert data["resource_usage"]["queue_length"] == 3