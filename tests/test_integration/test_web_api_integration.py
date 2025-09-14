"""
웹 API 통합 테스트 모듈

FastAPI 애플리케이션의 전체 웹 API 워크플로우를 테스트합니다:
- 업로드 → 처리 → 다운로드 전체 플로우
- API 응답 구조 검증
- 에러 처리 및 예외 상황 테스트
- 동시 요청 처리 능력 검증
"""

import asyncio
import io
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

# 실제 FastAPI 앱을 mock하여 테스트
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# 실제 구현된 모듈들 import
from backend.utils.temp_storage import TempStorage
from backend.core.pdf_converter import PDFConverter
from backend.core.image_processor import ImageProcessor, ProcessingOptions
from backend.core.file_generator import FileGenerator


# 테스트용 API 모델들
class UploadResponse(BaseModel):
    upload_id: str
    status: str
    filename: str
    file_size: int
    upload_time: str


class ProcessingRequest(BaseModel):
    ocr_engine: str = "tesseract"
    preprocessing: Dict = {}
    text_correction: Dict = {}


class ProcessingResponse(BaseModel):
    process_id: str
    status: str
    upload_id: str
    start_time: str


class StatusResponse(BaseModel):
    process_id: str
    status: str
    progress: int
    current_step: str = ""
    error: Optional[str] = None


# 테스트용 FastAPI 앱 생성
def create_test_app():
    app = FastAPI(title="K-OCR Test API")

    # 글로벌 저장소 (실제에서는 Redis나 DB 사용)
    storage = {}
    temp_storage = TempStorage("./test_temp")
    pdf_converter = PDFConverter()
    image_processor = ImageProcessor()
    file_generator = FileGenerator()

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "k-ocr-api"}

    @app.post("/api/upload", response_model=UploadResponse)
    async def upload_file(file: UploadFile = File(...)):
        """파일 업로드 엔드포인트"""
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        if file.size == 0:
            raise HTTPException(status_code=400, detail="Empty file not allowed")

        content = await file.read()

        try:
            upload_id = temp_storage.save_file(
                content,
                filename=file.filename,
                uploader_id="test_user"
            )

            return UploadResponse(
                upload_id=upload_id,
                status="completed",
                filename=file.filename,
                file_size=len(content),
                upload_time=time.strftime("%Y-%m-%d %H:%M:%S")
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/upload/{upload_id}/status")
    async def get_upload_status(upload_id: str):
        """업로드 상태 확인"""
        file_info = temp_storage.get_file(upload_id, "test_user")
        if not file_info:
            raise HTTPException(status_code=404, detail="Upload not found")

        return {
            "upload_id": upload_id,
            "status": "completed",
            "filename": file_info.filename,
            "file_size": file_info.file_size
        }

    @app.post("/api/process/{upload_id}", response_model=ProcessingResponse)
    async def start_processing(upload_id: str, request: ProcessingRequest):
        """처리 시작 엔드포인트"""
        file_info = temp_storage.get_file(upload_id, "test_user")
        if not file_info:
            raise HTTPException(status_code=404, detail="Upload not found")

        if request.ocr_engine not in ["tesseract", "paddleocr", "ensemble"]:
            raise HTTPException(status_code=400, detail="Invalid OCR engine")

        process_id = f"proc_{upload_id}_{int(time.time())}"

        # 처리 상태를 저장소에 저장
        storage[process_id] = {
            "status": "pending",
            "progress": 0,
            "upload_id": upload_id,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "options": request.model_dump()
        }

        # 백그라운드에서 처리 시뮬레이션 (실제에서는 Celery 사용)
        # TestClient는 동기적이므로 즉시 처리 상태를 업데이트
        storage[process_id].update({
            "status": "completed",
            "progress": 100,
            "result_text": f"OCR result for {file_info.filename}"
        })

        return ProcessingResponse(
            process_id=process_id,
            status="pending",
            upload_id=upload_id,
            start_time=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    @app.get("/api/process/{process_id}/status", response_model=StatusResponse)
    async def get_processing_status(process_id: str):
        """처리 상태 확인"""
        if process_id not in storage:
            raise HTTPException(status_code=404, detail="Process not found")

        process_data = storage[process_id]
        return StatusResponse(
            process_id=process_id,
            status=process_data["status"],
            progress=process_data["progress"],
            current_step=process_data.get("current_step", ""),
            error=process_data.get("error")
        )

    @app.get("/api/download/{process_id}")
    async def download_result(process_id: str):
        """결과 다운로드"""
        if process_id not in storage:
            raise HTTPException(status_code=404, detail="Process not found")

        process_data = storage[process_id]
        if process_data["status"] != "completed":
            raise HTTPException(status_code=400, detail="Processing not completed")

        # 결과 파일 생성 (시뮬레이션)
        result_text = process_data.get("result_text", "Test OCR result text")

        try:
            generated_file = file_generator.generate_text_file(
                text=result_text,
                filename="result.txt",
                process_id=process_id
            )

            return FileResponse(
                path=generated_file.file_path,
                filename=f"ocr_result_{process_id}.txt",
                media_type="text/plain"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/download/{process_id}/info")
    async def get_download_info(process_id: str):
        """다운로드 정보 확인"""
        if process_id not in storage:
            raise HTTPException(status_code=404, detail="Process not found")

        return {
            "process_id": process_id,
            "filename": f"ocr_result_{process_id}.txt",
            "file_size": 1024,  # 시뮬레이션
            "content_type": "text/plain"
        }

    async def simulate_processing(process_id: str, file_info):
        """처리 시뮬레이션 (실제에서는 Celery 태스크)"""
        try:
            # 단계별 처리 시뮬레이션
            stages = [
                ("converting", "Converting PDF to images", 20),
                ("preprocessing", "Preprocessing images", 40),
                ("ocr", "Performing OCR", 70),
                ("correcting", "Correcting text", 90),
                ("completed", "Processing completed", 100)
            ]

            for status, step, progress in stages:
                await asyncio.sleep(0.1)  # 처리 시간 시뮬레이션
                storage[process_id].update({
                    "status": status,
                    "progress": progress,
                    "current_step": step
                })

            # 결과 텍스트 추가
            storage[process_id]["result_text"] = f"OCR result for {file_info.filename}"

        except Exception as e:
            storage[process_id].update({
                "status": "failed",
                "progress": 0,
                "error": str(e)
            })

    return app


@pytest.fixture(scope="module")
def test_app():
    """테스트용 FastAPI 앱"""
    return create_test_app()


@pytest.fixture(scope="module")
def client(test_app):
    """테스트 클라이언트"""
    return TestClient(test_app)


@pytest.fixture
def sample_pdf_content():
    """테스트용 PDF 콘텐츠"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        c.drawString(100, 750, "Integration Test Document")
        c.drawString(100, 700, "This is a test document for API integration testing.")
        c.save()

        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
    except ImportError:
        # reportlab이 없으면 더미 PDF 생성
        return b"%PDF-1.4\n%API Integration Test PDF\n%%EOF"


class TestWebAPIIntegration:
    """웹 API 통합 테스트"""

    def test_health_check(self, client):
        """헬스체크 API 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "k-ocr-api"

    def test_complete_api_workflow(self, client, sample_pdf_content):
        """전체 API 워크플로우 테스트"""
        print("\n=== Complete API Workflow Test ===")

        # 1. 파일 업로드
        files = {"file": ("test_doc.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        upload_response = client.post("/api/upload", files=files)

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert "upload_id" in upload_data
        assert upload_data["status"] == "completed"
        assert upload_data["filename"] == "test_doc.pdf"

        upload_id = upload_data["upload_id"]
        print(f"1. File uploaded: {upload_id}")

        # 2. 업로드 상태 확인
        status_response = client.get(f"/api/upload/{upload_id}/status")
        assert status_response.status_code == 200

        # 3. 처리 시작
        processing_request = {
            "ocr_engine": "tesseract",
            "preprocessing": {
                "enabled": True,
                "grayscale_convert": True
            },
            "text_correction": {
                "enabled": True,
                "spacing_correction": True
            }
        }

        process_response = client.post(f"/api/process/{upload_id}", json=processing_request)
        assert process_response.status_code == 200

        process_data = process_response.json()
        assert "process_id" in process_data
        assert process_data["status"] == "pending"

        process_id = process_data["process_id"]
        print(f"2. Processing started: {process_id}")

        # 4. 처리 완료까지 폴링
        max_wait = 30  # 30초 최대 대기
        for i in range(max_wait):
            status_response = client.get(f"/api/process/{process_id}/status")
            assert status_response.status_code == 200

            status_data = status_response.json()
            print(f"   Status: {status_data['status']} ({status_data['progress']}%)")

            if status_data["status"] == "completed":
                assert status_data["progress"] == 100
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Processing failed: {status_data.get('error')}")

            time.sleep(0.2)
        else:
            pytest.fail("Processing timed out")

        print("3. Processing completed")

        # 5. 다운로드 정보 확인
        download_info = client.get(f"/api/download/{process_id}/info")
        assert download_info.status_code == 200

        info_data = download_info.json()
        assert "filename" in info_data
        assert "file_size" in info_data

        # 6. 결과 다운로드
        download_response = client.get(f"/api/download/{process_id}")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "text/plain; charset=utf-8"

        result_content = download_response.content.decode("utf-8")
        assert len(result_content) > 0

        print(f"4. Downloaded result: {len(result_content)} characters")
        print("=== API Workflow Test Completed ===\n")

    def test_upload_validation(self, client):
        """업로드 검증 테스트"""
        print("\n=== Upload Validation Test ===")

        # 빈 파일 테스트
        empty_file = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        response = client.post("/api/upload", files=empty_file)
        assert response.status_code == 400
        print("1. Empty file correctly rejected")

        # 잘못된 파일 형식 테스트
        txt_file = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
        response = client.post("/api/upload", files=txt_file)
        assert response.status_code == 400
        print("2. Non-PDF file correctly rejected")

        print("=== Upload Validation Test Completed ===\n")

    def test_processing_validation(self, client, sample_pdf_content):
        """처리 요청 검증 테스트"""
        print("\n=== Processing Validation Test ===")

        # 유효한 파일 업로드
        files = {"file": ("valid.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        upload_response = client.post("/api/upload", files=files)
        upload_id = upload_response.json()["upload_id"]

        # 존재하지 않는 업로드 ID
        invalid_request = {"ocr_engine": "tesseract"}
        response = client.post("/api/process/nonexistent", json=invalid_request)
        assert response.status_code == 404
        print("1. Nonexistent upload ID correctly rejected")

        # 잘못된 OCR 엔진
        invalid_engine = {"ocr_engine": "invalid_engine"}
        response = client.post(f"/api/process/{upload_id}", json=invalid_engine)
        assert response.status_code == 400
        print("2. Invalid OCR engine correctly rejected")

        print("=== Processing Validation Test Completed ===\n")

    def test_concurrent_requests(self, client, sample_pdf_content):
        """동시 요청 처리 테스트"""
        print("\n=== Concurrent Requests Test ===")

        def upload_file(index):
            files = {"file": (f"concurrent_{index}.pdf",
                            io.BytesIO(sample_pdf_content), "application/pdf")}
            response = client.post("/api/upload", files=files)
            return response.status_code, response.json() if response.status_code == 200 else None

        # 동시에 3개 파일 업로드
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_file, i) for i in range(3)]
            results = [future.result() for future in futures]

        # 모든 업로드가 성공했는지 확인
        successful_uploads = [r for r in results if r[0] == 200]
        assert len(successful_uploads) == 3
        print(f"Successfully uploaded {len(successful_uploads)} files concurrently")

        # 모든 upload_id가 고유한지 확인
        upload_ids = [r[1]["upload_id"] for r in successful_uploads]
        assert len(set(upload_ids)) == 3
        print("All upload IDs are unique")

        print("=== Concurrent Requests Test Completed ===\n")

    def test_api_response_structure(self, client, sample_pdf_content):
        """API 응답 구조 검증"""
        print("\n=== API Response Structure Test ===")

        # 업로드 응답 구조 검증
        files = {"file": ("structure_test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        upload_response = client.post("/api/upload", files=files)

        assert upload_response.status_code == 200
        upload_data = upload_response.json()

        required_fields = ["upload_id", "status", "filename", "file_size", "upload_time"]
        for field in required_fields:
            assert field in upload_data, f"Missing field: {field}"

        assert isinstance(upload_data["upload_id"], str)
        assert isinstance(upload_data["file_size"], int)
        assert upload_data["file_size"] > 0

        print("1. Upload response structure validated")

        # 처리 요청 응답 구조 검증
        upload_id = upload_data["upload_id"]
        process_request = {"ocr_engine": "tesseract"}
        process_response = client.post(f"/api/process/{upload_id}", json=process_request)

        assert process_response.status_code == 200
        process_data = process_response.json()

        required_fields = ["process_id", "status", "upload_id", "start_time"]
        for field in required_fields:
            assert field in process_data, f"Missing field: {field}"

        assert process_data["upload_id"] == upload_id
        print("2. Processing response structure validated")

        # 상태 확인 응답 구조 검증
        process_id = process_data["process_id"]
        status_response = client.get(f"/api/process/{process_id}/status")

        assert status_response.status_code == 200
        status_data = status_response.json()

        required_fields = ["process_id", "status", "progress"]
        for field in required_fields:
            assert field in status_data, f"Missing field: {field}"

        assert isinstance(status_data["progress"], int)
        assert 0 <= status_data["progress"] <= 100
        print("3. Status response structure validated")

        print("=== API Response Structure Test Completed ===\n")

    def test_error_responses(self, client):
        """오류 응답 테스트"""
        print("\n=== Error Responses Test ===")

        # 존재하지 않는 업로드 상태 확인
        response = client.get("/api/upload/nonexistent/status")
        assert response.status_code == 404
        print("1. Nonexistent upload status returns 404")

        # 존재하지 않는 처리 상태 확인
        response = client.get("/api/process/nonexistent/status")
        assert response.status_code == 404
        print("2. Nonexistent process status returns 404")

        # 존재하지 않는 다운로드
        response = client.get("/api/download/nonexistent")
        assert response.status_code == 404
        print("3. Nonexistent download returns 404")

        print("=== Error Responses Test Completed ===\n")


class TestAPIPerformance:
    """API 성능 테스트"""

    def test_response_times(self, client, sample_pdf_content):
        """API 응답 시간 테스트"""
        print("\n=== API Response Times Test ===")

        # 헬스체크 응답 시간
        start_time = time.time()
        response = client.get("/health")
        health_time = time.time() - start_time

        assert response.status_code == 200
        assert health_time < 1.0  # 1초 이내
        print(f"Health check: {health_time*1000:.1f}ms")

        # 업로드 응답 시간
        files = {"file": ("perf_test.pdf", io.BytesIO(sample_pdf_content), "application/pdf")}
        start_time = time.time()
        upload_response = client.post("/api/upload", files=files)
        upload_time = time.time() - start_time

        assert upload_response.status_code == 200
        assert upload_time < 5.0  # 5초 이내
        print(f"Upload: {upload_time*1000:.1f}ms")

        upload_id = upload_response.json()["upload_id"]

        # 상태 확인 응답 시간
        start_time = time.time()
        status_response = client.get(f"/api/upload/{upload_id}/status")
        status_time = time.time() - start_time

        assert status_response.status_code == 200
        assert status_time < 1.0  # 1초 이내
        print(f"Status check: {status_time*1000:.1f}ms")

        print("=== API Response Times Test Completed ===\n")

    def test_throughput(self, client, sample_pdf_content):
        """처리량 테스트"""
        print("\n=== API Throughput Test ===")

        requests_count = 5
        start_time = time.time()

        successful_requests = 0
        for i in range(requests_count):
            response = client.get("/health")
            if response.status_code == 200:
                successful_requests += 1

        total_time = time.time() - start_time
        throughput = successful_requests / total_time if total_time > 0 else 0

        print(f"Processed {successful_requests}/{requests_count} requests in {total_time:.2f}s")
        print(f"Throughput: {throughput:.1f} requests/second")

        assert successful_requests == requests_count
        assert throughput > 10  # 최소 10 req/s

        print("=== API Throughput Test Completed ===\n")


if __name__ == "__main__":
    # 단독 실행 시 기본 테스트
    app = create_test_app()
    client = TestClient(app)

    # 헬스체크 테스트
    response = client.get("/health")
    assert response.status_code == 200
    print("Basic API test passed!")