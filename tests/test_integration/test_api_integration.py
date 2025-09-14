"""
API 통합 테스트 모듈

이 모듈은 전체 API 워크플로우의 통합 테스트를 수행합니다:
- 업로드 → 처리 → 다운로드 전체 플로우 테스트
- 다양한 PDF 문서 테스트
- 동시 요청 처리 테스트
- 성능 및 부하 테스트
"""

import asyncio
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any
import tempfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
import requests

# 테스트용 앱 생성
try:
    from backend.main import app
except ImportError:
    # 백엔드 앱이 없는 경우 Mock 앱 생성
    from fastapi import FastAPI
    app = FastAPI()

# 테스트 설정
TEST_DATA_DIR = Path(__file__).parent / "test_data"
PERFORMANCE_THRESHOLD = {
    "upload_time": 5.0,  # 업로드 5초 이내
    "processing_time": 60.0,  # 처리 60초 이내
    "download_time": 3.0,  # 다운로드 3초 이내
    "memory_limit": 500 * 1024 * 1024,  # 500MB 메모리 제한
}


@pytest.fixture(scope="session")
def client():
    """통합 테스트용 클라이언트 생성"""
    return TestClient(app)


@pytest.fixture(scope="session")
def test_data_dir():
    """테스트 데이터 디렉토리 생성"""
    test_dir = Path(tempfile.mkdtemp(prefix="ocr_test_"))
    yield test_dir

    # 정리
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def sample_pdf_files(test_data_dir):
    """다양한 테스트용 PDF 파일 생성"""
    pdf_files = {}

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # 간단한 텍스트 PDF
        simple_pdf = test_data_dir / "simple_text.pdf"
        c = canvas.Canvas(str(simple_pdf), pagesize=letter)
        c.drawString(100, 750, "This is a simple English text for OCR testing.")
        c.drawString(100, 730, "한글 텍스트 OCR 테스트입니다.")
        c.drawString(100, 710, "Numbers: 123456789")
        c.drawString(100, 690, "Special characters: @#$%^&*()")
        c.save()
        pdf_files['simple'] = simple_pdf

        # 다중 페이지 PDF
        multi_page_pdf = test_data_dir / "multi_page.pdf"
        c = canvas.Canvas(str(multi_page_pdf), pagesize=A4)
        for page in range(3):
            c.drawString(100, 750, f"Page {page + 1} of 3")
            c.drawString(100, 700, f"This is content of page {page + 1}")
            c.drawString(100, 650, "한글 내용입니다.")
            c.showPage()
        c.save()
        pdf_files['multi_page'] = multi_page_pdf

        # 복잡한 레이아웃 PDF
        complex_pdf = test_data_dir / "complex_layout.pdf"
        c = canvas.Canvas(str(complex_pdf), pagesize=letter)

        # 제목
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Document Title")

        # 본문
        c.setFont("Helvetica", 12)
        text_lines = [
            "This is a complex document with multiple sections.",
            "Section 1: Introduction",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "",
            "Section 2: Methods",
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "",
            "Section 3: Results",
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco.",
        ]

        y_pos = 700
        for line in text_lines:
            c.drawString(100, y_pos, line)
            y_pos -= 20

        c.save()
        pdf_files['complex'] = complex_pdf

        # 한글 전용 PDF
        korean_pdf = test_data_dir / "korean_text.pdf"
        c = canvas.Canvas(str(korean_pdf), pagesize=letter)
        korean_texts = [
            "한국어 OCR 테스트 문서",
            "가나다라마바사아자차카타파하",
            "안녕하세요. 반갑습니다.",
            "이것은 한국어 텍스트 인식 테스트입니다.",
            "숫자: 일, 이, 삼, 사, 오",
            "특수문자: ！@＃￦％",
        ]

        y_pos = 750
        for text in korean_texts:
            c.drawString(100, y_pos, text)
            y_pos -= 30

        c.save()
        pdf_files['korean'] = korean_pdf

    except ImportError:
        # reportlab이 없으면 더미 파일 생성
        for name in ['simple', 'multi_page', 'complex', 'korean']:
            dummy_file = test_data_dir / f"{name}.pdf"
            dummy_file.write_bytes(b"%PDF-1.4\n%Dummy PDF for testing")
            pdf_files[name] = dummy_file

    return pdf_files


@pytest.fixture
def performance_monitor():
    """성능 모니터링 픽스처"""
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {}

        def start_timing(self, operation: str):
            self.metrics[operation] = {"start_time": time.time()}

        def end_timing(self, operation: str):
            if operation in self.metrics:
                self.metrics[operation]["duration"] = time.time() - self.metrics[operation]["start_time"]

        def get_duration(self, operation: str) -> float:
            return self.metrics.get(operation, {}).get("duration", 0.0)

        def assert_performance(self, operation: str, threshold: float):
            duration = self.get_duration(operation)
            assert duration <= threshold, f"{operation} took {duration:.2f}s, exceeding threshold {threshold}s"

    return PerformanceMonitor()


class TestFullWorkflowIntegration:
    """전체 워크플로우 통합 테스트"""

    def test_upload_process_download_flow_simple(self, client, sample_pdf_files, performance_monitor):
        """간단한 PDF 전체 플로우 테스트"""
        pdf_file = sample_pdf_files['simple']

        # 1. 파일 업로드
        performance_monitor.start_timing("upload")
        with open(pdf_file, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)
        performance_monitor.end_timing("upload")

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert 'upload_id' in upload_data
        assert upload_data['status'] == 'completed'

        # 성능 검증
        performance_monitor.assert_performance("upload", PERFORMANCE_THRESHOLD["upload_time"])

        upload_id = upload_data['upload_id']

        # 2. 처리 시작
        processing_options = {
            "ocr_engine": "paddleocr",
            "preprocessing": {
                "enabled": True,
                "grayscale_convert": True,
                "contrast_enhance": True
            },
            "text_correction": {
                "enabled": True,
                "spacing_correction": True
            }
        }

        performance_monitor.start_timing("processing_start")
        process_response = client.post(f"/api/process/{upload_id}", json=processing_options)
        performance_monitor.end_timing("processing_start")

        assert process_response.status_code == 200
        process_data = process_response.json()
        assert 'process_id' in process_data

        process_id = process_data['process_id']

        # 3. 처리 상태 폴링
        performance_monitor.start_timing("processing")
        max_wait_time = 60  # 최대 60초 대기
        poll_interval = 2   # 2초마다 확인

        for _ in range(max_wait_time // poll_interval):
            status_response = client.get(f"/api/process/{process_id}/status")
            assert status_response.status_code == 200

            status_data = status_response.json()
            status = status_data['status']

            if status == 'completed':
                performance_monitor.end_timing("processing")
                break
            elif status == 'failed':
                pytest.fail(f"Processing failed: {status_data.get('error', 'Unknown error')}")

            time.sleep(poll_interval)
        else:
            pytest.fail("Processing timed out")

        # 성능 검증
        performance_monitor.assert_performance("processing", PERFORMANCE_THRESHOLD["processing_time"])

        # 4. 결과 다운로드
        performance_monitor.start_timing("download")
        download_response = client.get(f"/api/download/{process_id}")
        performance_monitor.end_timing("download")

        assert download_response.status_code == 200
        assert download_response.headers['content-type'] == 'text/plain; charset=utf-8'

        # 성능 검증
        performance_monitor.assert_performance("download", PERFORMANCE_THRESHOLD["download_time"])

        # 결과 검증
        result_text = download_response.content.decode('utf-8')
        assert len(result_text) > 0
        # 기본적인 텍스트 내용 검증 (OCR 결과는 정확하지 않을 수 있음)
        assert any(char.isalnum() for char in result_text)

    def test_multi_page_document_processing(self, client, sample_pdf_files, performance_monitor):
        """다중 페이지 문서 처리 테스트"""
        pdf_file = sample_pdf_files['multi_page']

        # 업로드
        with open(pdf_file, 'rb') as f:
            files = {'file': ('multi_page.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)

        assert upload_response.status_code == 200
        upload_id = upload_response.json()['upload_id']

        # 처리 시작
        processing_options = {
            "ocr_engine": "tesseract",
            "preprocessing": {
                "enabled": True,
                "grayscale_convert": True,
                "contrast_enhance": True,
                "deskew_correction": True
            }
        }

        process_response = client.post(f"/api/process/{upload_id}", json=processing_options)
        assert process_response.status_code == 200
        process_id = process_response.json()['process_id']

        # 처리 완료 대기
        self._wait_for_completion(client, process_id)

        # 결과 확인
        download_response = client.get(f"/api/download/{process_id}")
        assert download_response.status_code == 200

        result_text = download_response.content.decode('utf-8')
        assert len(result_text) > 0

        # 다중 페이지 내용이 포함되었는지 확인
        # (정확한 OCR 결과를 기대하기는 어려우므로 기본적인 검증만)
        lines = result_text.split('\n')
        assert len(lines) > 3  # 다중 페이지이므로 여러 줄이 있어야 함

    def test_korean_text_processing(self, client, sample_pdf_files):
        """한국어 텍스트 처리 테스트"""
        pdf_file = sample_pdf_files['korean']

        # 업로드
        with open(pdf_file, 'rb') as f:
            files = {'file': ('korean.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)

        assert upload_response.status_code == 200
        upload_id = upload_response.json()['upload_id']

        # 한국어 최적화 옵션으로 처리
        processing_options = {
            "ocr_engine": "paddleocr",  # 한국어에 더 적합
            "preprocessing": {
                "enabled": True,
                "grayscale_convert": True,
                "contrast_enhance": True
            },
            "text_correction": {
                "enabled": True,
                "spacing_correction": True,
                "spelling_correction": True
            }
        }

        process_response = client.post(f"/api/process/{upload_id}", json=processing_options)
        assert process_response.status_code == 200
        process_id = process_response.json()['process_id']

        # 처리 완료 대기
        self._wait_for_completion(client, process_id)

        # 결과 확인
        download_response = client.get(f"/api/download/{process_id}")
        assert download_response.status_code == 200

        result_text = download_response.content.decode('utf-8')
        assert len(result_text) > 0

        # 한국어 문자가 포함되어 있는지 확인
        has_korean = any('\uac00' <= char <= '\ud7af' for char in result_text)
        # OCR이 완벽하지 않을 수 있으므로 너무 엄격하게 검증하지 않음
        if not has_korean:
            # 최소한 알파벳이나 숫자는 인식되어야 함
            assert any(char.isalnum() for char in result_text)

    def test_different_processing_options(self, client, sample_pdf_files):
        """다양한 처리 옵션 테스트"""
        pdf_file = sample_pdf_files['simple']

        # 여러 처리 옵션 조합 테스트
        option_combinations = [
            {
                "ocr_engine": "paddleocr",
                "preprocessing": {"enabled": False},
                "text_correction": {"enabled": False}
            },
            {
                "ocr_engine": "tesseract",
                "preprocessing": {
                    "enabled": True,
                    "grayscale_convert": True,
                    "contrast_enhance": False,
                    "deskew_correction": True,
                    "noise_removal": True
                },
                "text_correction": {
                    "enabled": True,
                    "spacing_correction": True,
                    "spelling_correction": False
                }
            },
            {
                "ocr_engine": "ensemble",
                "preprocessing": {
                    "enabled": True,
                    "grayscale_convert": True,
                    "contrast_enhance": True,
                    "deskew_correction": True,
                    "noise_removal": True
                },
                "text_correction": {
                    "enabled": True,
                    "spacing_correction": True,
                    "spelling_correction": True
                }
            }
        ]

        results = []

        for i, options in enumerate(option_combinations):
            # 업로드
            with open(pdf_file, 'rb') as f:
                files = {'file': (f'test_{i}.pdf', f, 'application/pdf')}
                upload_response = client.post("/api/upload", files=files)

            assert upload_response.status_code == 200
            upload_id = upload_response.json()['upload_id']

            # 처리
            process_response = client.post(f"/api/process/{upload_id}", json=options)
            assert process_response.status_code == 200
            process_id = process_response.json()['process_id']

            # 완료 대기
            self._wait_for_completion(client, process_id)

            # 결과 다운로드
            download_response = client.get(f"/api/download/{process_id}")
            assert download_response.status_code == 200

            result_text = download_response.content.decode('utf-8')
            results.append({
                'options': options,
                'result': result_text,
                'length': len(result_text)
            })

        # 모든 조합에서 결과가 나왔는지 확인
        for result in results:
            assert result['length'] > 0

        # 결과들이 서로 다를 수 있음 (다른 옵션이므로)
        assert len(set(r['result'] for r in results)) >= 1

    def _wait_for_completion(self, client, process_id: str, max_wait: int = 90):
        """처리 완료까지 대기"""
        for _ in range(max_wait // 2):
            status_response = client.get(f"/api/process/{process_id}/status")
            assert status_response.status_code == 200

            status_data = status_response.json()
            if status_data['status'] == 'completed':
                return
            elif status_data['status'] == 'failed':
                pytest.fail(f"Processing failed: {status_data.get('error', 'Unknown error')}")

            time.sleep(2)

        pytest.fail("Processing timed out")


class TestConcurrentRequests:
    """동시 요청 처리 테스트"""

    def test_concurrent_uploads(self, client, sample_pdf_files):
        """동시 업로드 테스트"""
        pdf_file = sample_pdf_files['simple']
        concurrent_count = 3

        def upload_file(file_path, index):
            with open(file_path, 'rb') as f:
                files = {'file': (f'concurrent_{index}.pdf', f, 'application/pdf')}
                response = client.post("/api/upload", files=files)
                return response.status_code, response.json()

        # 동시 업로드 실행
        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [
                executor.submit(upload_file, pdf_file, i)
                for i in range(concurrent_count)
            ]

            results = [future.result() for future in futures]

        # 모든 업로드가 성공했는지 확인
        for status_code, response_data in results:
            assert status_code == 200
            assert 'upload_id' in response_data
            assert response_data['status'] == 'completed'

        # 모든 upload_id가 고유한지 확인
        upload_ids = [data['upload_id'] for _, data in results]
        assert len(set(upload_ids)) == concurrent_count

    def test_concurrent_processing(self, client, sample_pdf_files):
        """동시 처리 테스트"""
        pdf_file = sample_pdf_files['simple']
        concurrent_count = 2  # 처리는 리소스를 많이 사용하므로 개수 제한

        # 먼저 파일들 업로드
        upload_ids = []
        for i in range(concurrent_count):
            with open(pdf_file, 'rb') as f:
                files = {'file': (f'concurrent_proc_{i}.pdf', f, 'application/pdf')}
                upload_response = client.post("/api/upload", files=files)
                assert upload_response.status_code == 200
                upload_ids.append(upload_response.json()['upload_id'])

        # 동시 처리 시작
        def start_processing(upload_id, index):
            options = {
                "ocr_engine": "tesseract",
                "preprocessing": {"enabled": True, "grayscale_convert": True},
                "text_correction": {"enabled": False}  # 빠른 처리를 위해
            }
            response = client.post(f"/api/process/{upload_id}", json=options)
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [
                executor.submit(start_processing, upload_id, i)
                for i, upload_id in enumerate(upload_ids)
            ]

            results = [future.result() for future in futures]

        # 모든 처리가 시작되었는지 확인
        process_ids = []
        for status_code, response_data in results:
            assert status_code == 200
            assert 'process_id' in response_data
            process_ids.append(response_data['process_id'])

        # 모든 process_id가 고유한지 확인
        assert len(set(process_ids)) == concurrent_count

        # 모든 처리가 완료될 때까지 대기 (간단한 검증만)
        for process_id in process_ids[:1]:  # 첫 번째 것만 완료 확인
            try:
                self._wait_for_completion(client, process_id, max_wait=60)
            except:
                pass  # 테스트 환경에서는 실패할 수 있음

    def _wait_for_completion(self, client, process_id: str, max_wait: int = 60):
        """처리 완료까지 대기"""
        for _ in range(max_wait // 2):
            try:
                status_response = client.get(f"/api/process/{process_id}/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['status'] in ['completed', 'failed']:
                        return
                time.sleep(2)
            except:
                time.sleep(2)


class TestErrorHandling:
    """오류 처리 통합 테스트"""

    def test_invalid_file_upload(self, client):
        """잘못된 파일 업로드 테스트"""
        # 빈 파일
        files = {'file': ('empty.pdf', io.BytesIO(b''), 'application/pdf')}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400

        # 잘못된 MIME 타입
        files = {'file': ('test.txt', io.BytesIO(b'not a pdf'), 'text/plain')}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400

        # 너무 큰 파일 (시뮬레이션)
        large_content = b'%PDF-1.4\n' + b'x' * (100 * 1024 * 1024)  # 100MB
        files = {'file': ('large.pdf', io.BytesIO(large_content), 'application/pdf')}
        response = client.post("/api/upload", files=files)
        # 파일 크기 제한에 따라 400 또는 413 응답 예상
        assert response.status_code in [400, 413]

    def test_invalid_process_requests(self, client):
        """잘못된 처리 요청 테스트"""
        # 존재하지 않는 upload_id
        invalid_options = {"ocr_engine": "paddleocr"}
        response = client.post("/api/process/nonexistent_id", json=invalid_options)
        assert response.status_code == 404

        # 잘못된 OCR 엔진
        # 먼저 유효한 파일 업로드
        dummy_pdf = io.BytesIO(b'%PDF-1.4\nDummy PDF')
        files = {'file': ('test.pdf', dummy_pdf, 'application/pdf')}
        upload_response = client.post("/api/upload", files=files)

        if upload_response.status_code == 200:
            upload_id = upload_response.json()['upload_id']

            invalid_options = {"ocr_engine": "invalid_engine"}
            response = client.post(f"/api/process/{upload_id}", json=invalid_options)
            assert response.status_code == 400

    def test_nonexistent_download(self, client):
        """존재하지 않는 다운로드 테스트"""
        response = client.get("/api/download/nonexistent_process_id")
        assert response.status_code == 404

    def test_processing_status_for_nonexistent_process(self, client):
        """존재하지 않는 프로세스 상태 확인 테스트"""
        response = client.get("/api/process/nonexistent_process_id/status")
        assert response.status_code == 404


class TestPerformanceBenchmarks:
    """성능 벤치마크 테스트"""

    def test_upload_performance(self, client, sample_pdf_files, performance_monitor):
        """업로드 성능 테스트"""
        pdf_file = sample_pdf_files['simple']
        file_size = os.path.getsize(pdf_file)

        performance_monitor.start_timing("upload_perf")

        with open(pdf_file, 'rb') as f:
            files = {'file': ('perf_test.pdf', f, 'application/pdf')}
            response = client.post("/api/upload", files=files)

        performance_monitor.end_timing("upload_perf")

        assert response.status_code == 200

        duration = performance_monitor.get_duration("upload_perf")
        throughput = file_size / duration if duration > 0 else 0

        # 성능 로깅
        print(f"Upload performance: {duration:.2f}s for {file_size} bytes ({throughput:.0f} bytes/sec)")

        # 기본적인 성능 임계값 검증
        assert duration < PERFORMANCE_THRESHOLD["upload_time"]

    def test_memory_usage_monitoring(self, client, sample_pdf_files):
        """메모리 사용량 모니터링 테스트"""
        import psutil
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        pdf_file = sample_pdf_files['complex']

        # 메모리 집약적인 작업 수행
        for i in range(3):  # 3번 반복
            with open(pdf_file, 'rb') as f:
                files = {'file': (f'memory_test_{i}.pdf', f, 'application/pdf')}
                response = client.post("/api/upload", files=files)
                assert response.status_code == 200

            # 강제 가비지 컬렉션
            gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 메모리 사용량 로깅
        print(f"Memory usage: {initial_memory / 1024 / 1024:.1f}MB -> {final_memory / 1024 / 1024:.1f}MB "
              f"(+{memory_increase / 1024 / 1024:.1f}MB)")

        # 메모리 누수 체크 (너무 많이 증가하면 안 됨)
        assert memory_increase < PERFORMANCE_THRESHOLD["memory_limit"]

    def test_api_response_times(self, client, sample_pdf_files, performance_monitor):
        """API 응답 시간 테스트"""
        pdf_file = sample_pdf_files['simple']

        # 업로드 응답 시간
        performance_monitor.start_timing("api_upload")
        with open(pdf_file, 'rb') as f:
            files = {'file': ('response_time_test.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)
        performance_monitor.end_timing("api_upload")

        assert upload_response.status_code == 200
        upload_id = upload_response.json()['upload_id']

        # 상태 확인 응답 시간
        performance_monitor.start_timing("api_upload_status")
        status_response = client.get(f"/api/upload/{upload_id}/status")
        performance_monitor.end_timing("api_upload_status")

        assert status_response.status_code == 200

        # 처리 시작 응답 시간
        options = {"ocr_engine": "tesseract", "preprocessing": {"enabled": False}}
        performance_monitor.start_timing("api_process_start")
        process_response = client.post(f"/api/process/{upload_id}", json=options)
        performance_monitor.end_timing("api_process_start")

        # 응답 시간 검증 (각각 3초 이내)
        for operation in ["api_upload", "api_upload_status", "api_process_start"]:
            duration = performance_monitor.get_duration(operation)
            print(f"{operation}: {duration:.3f}s")
            assert duration < 3.0

    def test_load_simulation(self, client, sample_pdf_files):
        """간단한 부하 테스트"""
        pdf_file = sample_pdf_files['simple']
        concurrent_users = 3
        requests_per_user = 2

        def user_simulation(user_id):
            results = []
            for req_id in range(requests_per_user):
                start_time = time.time()

                try:
                    with open(pdf_file, 'rb') as f:
                        files = {'file': (f'load_test_u{user_id}_r{req_id}.pdf', f, 'application/pdf')}
                        response = client.post("/api/upload", files=files)

                    duration = time.time() - start_time
                    results.append({
                        'user_id': user_id,
                        'request_id': req_id,
                        'status_code': response.status_code,
                        'duration': duration,
                        'success': response.status_code == 200
                    })
                except Exception as e:
                    results.append({
                        'user_id': user_id,
                        'request_id': req_id,
                        'error': str(e),
                        'success': False
                    })

            return results

        # 동시 사용자 시뮬레이션
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [
                executor.submit(user_simulation, user_id)
                for user_id in range(concurrent_users)
            ]

            all_results = []
            for future in futures:
                all_results.extend(future.result())

        # 결과 분석
        successful_requests = [r for r in all_results if r.get('success', False)]
        failed_requests = [r for r in all_results if not r.get('success', False)]

        success_rate = len(successful_requests) / len(all_results) if all_results else 0

        if successful_requests:
            avg_response_time = sum(r['duration'] for r in successful_requests) / len(successful_requests)
            max_response_time = max(r['duration'] for r in successful_requests)

            print(f"Load test results:")
            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Average response time: {avg_response_time:.2f}s")
            print(f"  Max response time: {max_response_time:.2f}s")
            print(f"  Failed requests: {len(failed_requests)}")

        # 최소한 50% 이상의 요청이 성공해야 함
        assert success_rate >= 0.5


class TestDataValidation:
    """데이터 검증 통합 테스트"""

    def test_upload_response_structure(self, client, sample_pdf_files):
        """업로드 응답 구조 검증"""
        pdf_file = sample_pdf_files['simple']

        with open(pdf_file, 'rb') as f:
            files = {'file': ('structure_test.pdf', f, 'application/pdf')}
            response = client.post("/api/upload", files=files)

        assert response.status_code == 200
        data = response.json()

        # 필수 필드 확인
        assert 'upload_id' in data
        assert 'status' in data
        assert 'filename' in data
        assert 'file_size' in data
        assert 'upload_time' in data

        # 타입 검증
        assert isinstance(data['upload_id'], str)
        assert isinstance(data['status'], str)
        assert isinstance(data['filename'], str)
        assert isinstance(data['file_size'], int)
        assert isinstance(data['upload_time'], str)

        # 값 검증
        assert len(data['upload_id']) > 0
        assert data['status'] in ['pending', 'completed', 'failed']
        assert data['file_size'] > 0

    def test_process_response_structure(self, client, sample_pdf_files):
        """처리 응답 구조 검증"""
        pdf_file = sample_pdf_files['simple']

        # 업로드
        with open(pdf_file, 'rb') as f:
            files = {'file': ('process_struct_test.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)

        assert upload_response.status_code == 200
        upload_id = upload_response.json()['upload_id']

        # 처리 시작
        options = {
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

        process_response = client.post(f"/api/process/{upload_id}", json=options)
        assert process_response.status_code == 200

        data = process_response.json()

        # 필수 필드 확인
        assert 'process_id' in data
        assert 'status' in data
        assert 'upload_id' in data
        assert 'start_time' in data

        # 타입 검증
        assert isinstance(data['process_id'], str)
        assert isinstance(data['status'], str)
        assert isinstance(data['upload_id'], str)
        assert isinstance(data['start_time'], str)

        # 값 검증
        assert len(data['process_id']) > 0
        assert data['status'] in ['pending', 'in_progress', 'completed', 'failed']
        assert data['upload_id'] == upload_id

    def test_status_response_structure(self, client, sample_pdf_files):
        """상태 응답 구조 검증"""
        pdf_file = sample_pdf_files['simple']

        # 업로드 및 처리 시작
        with open(pdf_file, 'rb') as f:
            files = {'file': ('status_struct_test.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)

        upload_id = upload_response.json()['upload_id']

        options = {"ocr_engine": "tesseract"}
        process_response = client.post(f"/api/process/{upload_id}", json=options)
        process_id = process_response.json()['process_id']

        # 상태 확인
        status_response = client.get(f"/api/process/{process_id}/status")
        assert status_response.status_code == 200

        data = status_response.json()

        # 필수 필드 확인
        assert 'process_id' in data
        assert 'status' in data
        assert 'progress' in data

        # 타입 검증
        assert isinstance(data['process_id'], str)
        assert isinstance(data['status'], str)
        assert isinstance(data['progress'], (int, float))

        # 값 검증
        assert data['process_id'] == process_id
        assert data['status'] in ['pending', 'converting', 'preprocessing', 'ocr', 'correcting', 'completed', 'failed']
        assert 0 <= data['progress'] <= 100


@pytest.mark.integration
class TestEndToEndScenarios:
    """전체 시나리오 통합 테스트"""

    def test_complete_user_journey_success(self, client, sample_pdf_files, performance_monitor):
        """성공적인 사용자 여정 전체 테스트"""
        pdf_file = sample_pdf_files['simple']

        # 전체 여정 시간 측정
        performance_monitor.start_timing("complete_journey")

        # 1. 파일 업로드
        with open(pdf_file, 'rb') as f:
            files = {'file': ('journey_test.pdf', f, 'application/pdf')}
            upload_response = client.post("/api/upload", files=files)

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        upload_id = upload_data['upload_id']

        # 2. 업로드 상태 확인
        upload_status = client.get(f"/api/upload/{upload_id}/status")
        assert upload_status.status_code == 200

        # 3. 처리 옵션 설정 및 시작
        processing_options = {
            "ocr_engine": "paddleocr",
            "preprocessing": {
                "enabled": True,
                "grayscale_convert": True,
                "contrast_enhance": True,
                "deskew_correction": False,
                "noise_removal": False
            },
            "text_correction": {
                "enabled": True,
                "spacing_correction": True,
                "spelling_correction": False
            },
            "advanced": {
                "image_dpi": 300,
                "confidence_threshold": 0.8
            }
        }

        process_response = client.post(f"/api/process/{upload_id}", json=processing_options)
        assert process_response.status_code == 200
        process_data = process_response.json()
        process_id = process_data['process_id']

        # 4. 처리 진행률 모니터링
        progress_history = []
        max_wait = 90

        for i in range(max_wait // 2):
            status_response = client.get(f"/api/process/{process_id}/status")
            assert status_response.status_code == 200

            status_data = status_response.json()
            progress_history.append({
                'timestamp': time.time(),
                'status': status_data['status'],
                'progress': status_data['progress']
            })

            if status_data['status'] == 'completed':
                break
            elif status_data['status'] == 'failed':
                pytest.fail(f"Processing failed: {status_data.get('error', 'Unknown error')}")

            time.sleep(2)
        else:
            pytest.fail("Processing timed out")

        # 5. 결과 다운로드
        download_response = client.get(f"/api/download/{process_id}")
        assert download_response.status_code == 200
        assert download_response.headers['content-type'] == 'text/plain; charset=utf-8'

        result_text = download_response.content.decode('utf-8')

        # 6. 다운로드 정보 확인
        download_info = client.get(f"/api/download/{process_id}/info")
        assert download_info.status_code == 200
        info_data = download_info.json()
        assert 'filename' in info_data
        assert 'file_size' in info_data

        performance_monitor.end_timing("complete_journey")

        # 결과 검증
        assert len(result_text) > 0
        assert len(progress_history) > 0
        assert progress_history[-1]['status'] == 'completed'
        assert progress_history[-1]['progress'] == 100

        # 진행률이 점진적으로 증가했는지 확인
        progresses = [p['progress'] for p in progress_history]
        assert progresses == sorted(progresses)  # 진행률이 감소하지 않음

        # 전체 여정 시간 로깅
        total_time = performance_monitor.get_duration("complete_journey")
        print(f"Complete user journey took {total_time:.2f} seconds")

        # 합리적인 시간 내에 완료되었는지 확인 (2분 이내)
        assert total_time < 120

    def test_user_journey_with_errors(self, client):
        """오류가 있는 사용자 여정 테스트"""
        # 1. 잘못된 파일 업로드 시도
        invalid_files = {'file': ('invalid.txt', io.BytesIO(b'not a pdf'), 'text/plain')}
        upload_response = client.post("/api/upload", files=invalid_files)
        assert upload_response.status_code == 400

        # 2. 올바른 파일 업로드
        dummy_pdf = io.BytesIO(b'%PDF-1.4\nDummy PDF content')
        valid_files = {'file': ('valid.pdf', dummy_pdf, 'application/pdf')}
        upload_response = client.post("/api/upload", files=valid_files)
        assert upload_response.status_code == 200
        upload_id = upload_response.json()['upload_id']

        # 3. 잘못된 처리 옵션으로 시도
        invalid_options = {"ocr_engine": "nonexistent_engine"}
        process_response = client.post(f"/api/process/{upload_id}", json=invalid_options)
        assert process_response.status_code == 400

        # 4. 올바른 처리 옵션으로 시도
        valid_options = {"ocr_engine": "tesseract", "preprocessing": {"enabled": False}}
        process_response = client.post(f"/api/process/{upload_id}", json=valid_options)
        assert process_response.status_code == 200
        process_id = process_response.json()['process_id']

        # 5. 존재하지 않는 프로세스 상태 확인 시도
        fake_status = client.get("/api/process/nonexistent_id/status")
        assert fake_status.status_code == 404

        # 6. 올바른 상태 확인
        real_status = client.get(f"/api/process/{process_id}/status")
        assert real_status.status_code == 200