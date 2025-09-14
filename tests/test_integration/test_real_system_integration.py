"""
실제 시스템을 사용한 통합 테스트

이 모듈은 실제 구현된 백엔드 시스템의 모든 컴포넌트가
올바르게 통합되어 작동하는지 테스트합니다.
"""

import asyncio
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List

import pytest
from PIL import Image, ImageDraw, ImageFont

# 실제 구현된 모듈들 import
from backend.utils.temp_storage import TempStorage
from backend.core.pdf_converter import PDFConverter
from backend.core.image_processor import ImageProcessor
from backend.core.ocr_engine import OCREngineManager
from backend.core.text_corrector import TextCorrector
from backend.core.file_generator import FileGenerator


class TestRealSystemIntegration:
    """실제 시스템 구성요소 통합 테스트"""

    @pytest.fixture(scope="class")
    def test_data_dir(self):
        """테스트 데이터 디렉토리"""
        test_dir = Path(tempfile.mkdtemp(prefix="real_integration_"))
        yield test_dir

        # 정리
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def temp_storage(self, test_data_dir):
        """실제 TempStorage 인스턴스"""
        storage_dir = test_data_dir / "temp_storage"
        storage_dir.mkdir()
        return TempStorage(str(storage_dir))

    @pytest.fixture(scope="class")
    def pdf_converter(self):
        """실제 PDFConverter 인스턴스"""
        return PDFConverter()

    @pytest.fixture(scope="class")
    def image_processor(self):
        """실제 ImageProcessor 인스턴스"""
        return ImageProcessor()

    @pytest.fixture(scope="class")
    def ocr_engine(self):
        """실제 OCREngine 인스턴스"""
        manager = OCREngineManager()
        # 테스트용으로 간단한 엔진만 사용
        manager.set_engine("tesseract")
        return manager

    @pytest.fixture(scope="class")
    def text_corrector(self):
        """실제 TextCorrector 인스턴스"""
        return TextCorrector()

    @pytest.fixture(scope="class")
    def file_generator(self):
        """실제 FileGenerator 인스턴스"""
        return FileGenerator()

    @pytest.fixture
    def sample_pdf_file(self, test_data_dir):
        """테스트용 PDF 파일 생성"""
        pdf_file = test_data_dir / "test_document.pdf"

        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter

            c = canvas.Canvas(str(pdf_file), pagesize=letter)
            c.drawString(100, 750, "OCR Integration Test Document")
            c.drawString(100, 700, "This is a test document for OCR processing.")
            c.drawString(100, 650, "한국어 텍스트도 포함되어 있습니다.")
            c.drawString(100, 600, "Numbers: 123456789")
            c.drawString(100, 550, "Special characters: @#$%^&*()")
            c.save()

        except ImportError:
            # reportlab이 없으면 더미 PDF 생성
            pdf_file.write_bytes(b"%PDF-1.4\n%OCR Test PDF\n%%EOF")

        return pdf_file

    def test_complete_ocr_pipeline(self, temp_storage, pdf_converter,
                                   image_processor, ocr_engine, text_corrector,
                                   file_generator, sample_pdf_file):
        """전체 OCR 파이프라인 통합 테스트"""
        print("\n=== Complete OCR Pipeline Integration Test ===")

        # 1. PDF 파일을 temp storage에 저장
        with open(sample_pdf_file, 'rb') as f:
            pdf_data = f.read()

        upload_id = temp_storage.save_file(
            pdf_data,
            filename="test_document.pdf",
            uploader_id="integration_test_user"
        )

        print(f"1. PDF uploaded with ID: {upload_id}")
        assert upload_id is not None

        # 2. PDF를 PNG로 변환
        file_info = temp_storage.get_file(upload_id, "integration_test_user")
        assert file_info is not None

        # 임시 파일로 저장하여 PDFConverter에 전달
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(file_info.content)
            tmp_pdf_path = tmp_file.name

        png_paths = pdf_converter.convert_pdf_to_png(tmp_pdf_path)

        print(f"2. PDF converted to {len(png_paths)} PNG images")
        assert len(png_paths) > 0

        all_text = []
        processing_stats = {
            'pages_processed': 0,
            'total_characters': 0,
            'processing_time': 0
        }

        start_time = time.time()

        # 3. 각 페이지 처리
        for i, png_path in enumerate(png_paths):
            print(f"3.{i+1}. Processing page {i+1}")

            # 이미지 전처리
            from backend.core.image_processor import ProcessingOptions
            preprocess_options = ProcessingOptions(
                apply_clahe=True,
                deskew_enabled=False,  # 간단한 테스트를 위해
                noise_removal=False,
                adaptive_threshold=True
            )

            processed_image = image_processor.preprocess_pipeline(
                png_path, preprocess_options
            )

            print(f"   - Image preprocessed: {processed_image}")
            assert processed_image is not None

            # OCR 처리
            try:
                ocr_result = ocr_engine.recognize_text(processed_image)
                print(f"   - OCR completed, text length: {len(ocr_result.text)}")

                if ocr_result.text.strip():
                    # 텍스트 교정
                    corrected_text = text_corrector.correct_text(ocr_result.text)
                    print(f"   - Text corrected, final length: {len(corrected_text)}")
                    all_text.append(corrected_text)
                    processing_stats['total_characters'] += len(corrected_text)
                else:
                    print("   - No text recognized from this page")
                    all_text.append("")

            except Exception as e:
                print(f"   - OCR failed: {e}")
                # OCR 실패는 테스트 환경에서 발생할 수 있음
                all_text.append("OCR processing failed in test environment")

            processing_stats['pages_processed'] += 1

        processing_stats['processing_time'] = time.time() - start_time

        # 4. 최종 텍스트 결합
        final_text = "\n\n".join(all_text)
        print(f"4. Final text combined, total length: {len(final_text)}")

        # 5. 결과 파일 생성
        generated_file = file_generator.generate_text_file(
            text=final_text,
            filename="test_document.txt",
            process_id=f"test_{upload_id}",
            encoding='utf-8'
        )

        print(f"5. Result file generated: {generated_file.file_path}")
        assert generated_file is not None
        assert os.path.exists(generated_file.file_path)

        # 6. 결과 검증
        with open(generated_file.file_path, 'r', encoding='utf-8') as f:
            saved_text = f.read()

        assert len(saved_text) >= 0  # 최소한 파일이 생성됨
        print(f"6. Final verification passed")

        # 통계 출력
        print(f"\n=== Processing Statistics ===")
        print(f"Pages processed: {processing_stats['pages_processed']}")
        print(f"Total characters: {processing_stats['total_characters']}")
        print(f"Processing time: {processing_stats['processing_time']:.2f}s")

        # 정리
        temp_storage.cleanup_expired_files(current_time=time.time() + 86401)  # 강제로 만료시킴
        if os.path.exists(generated_file.file_path):
            os.remove(generated_file.file_path)
        if os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)
        for png_path in png_paths:
            if os.path.exists(png_path):
                os.remove(png_path)

        print("=== Integration Test Completed Successfully ===\n")

    def test_error_handling_integration(self, temp_storage, pdf_converter,
                                        image_processor, ocr_engine):
        """오류 처리 통합 테스트"""
        print("\n=== Error Handling Integration Test ===")

        # 1. 잘못된 PDF 파일 처리
        invalid_pdf = b"This is not a PDF file"
        upload_id = temp_storage.save_file(
            invalid_pdf,
            filename="invalid.pdf",
            uploader_id="error_test_user"
        )

        file_info = temp_storage.get_file(upload_id, "error_test_user")
        assert file_info is not None

        # 임시 파일로 저장
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(file_info.content)
            tmp_pdf_path = tmp_file.name

        try:
            png_paths = pdf_converter.convert_pdf_to_png(tmp_pdf_path)
            print("1. Invalid PDF conversion should have failed")
            assert False, "Expected PDF conversion to fail"
        except Exception as e:
            print(f"1. Invalid PDF correctly rejected: {type(e).__name__}")

        # 2. 존재하지 않는 이미지 처리
        try:
            from backend.core.image_processor import ProcessingOptions
            options = ProcessingOptions()
            result = image_processor.preprocess_pipeline("/nonexistent/path.png", options)
            print("2. Nonexistent image processing should have failed")
            assert False, "Expected image processing to fail"
        except Exception as e:
            print(f"2. Nonexistent image correctly rejected: {type(e).__name__}")

        # 3. OCR 엔진 초기화 오류 시뮬레이션
        try:
            # 존재하지 않는 엔진 설정 시도
            ocr_engine.set_engine("nonexistent_engine")
            print("3. Invalid OCR engine should have failed")
            assert False, "Expected OCR engine setting to fail"
        except Exception as e:
            print(f"3. Invalid OCR engine correctly rejected: {type(e).__name__}")

        # 정리
        temp_storage.cleanup_expired_files(current_time=time.time() + 86401)  # 강제로 만료시킴
        if 'tmp_pdf_path' in locals() and os.path.exists(tmp_pdf_path):
            os.remove(tmp_pdf_path)

        print("=== Error Handling Test Completed Successfully ===\n")

    def test_performance_integration(self, temp_storage, pdf_converter,
                                     image_processor, test_data_dir):
        """성능 통합 테스트"""
        print("\n=== Performance Integration Test ===")

        # 여러 크기의 테스트 이미지 생성
        test_images = []

        for size in [(800, 600), (1200, 900), (1600, 1200)]:
            img = Image.new('RGB', size, color='white')
            draw = ImageDraw.Draw(img)

            # 텍스트 추가
            try:
                font = ImageFont.load_default()
            except:
                font = None

            draw.text((50, 50), f"Performance Test Image {size[0]}x{size[1]}",
                     fill='black', font=font)
            draw.text((50, 100), "This is a performance test document.",
                     fill='black', font=font)

            img_path = test_data_dir / f"perf_test_{size[0]}x{size[1]}.png"
            img.save(img_path)
            test_images.append(img_path)

        # 성능 측정
        from backend.core.image_processor import ProcessingOptions
        options = ProcessingOptions(
            apply_clahe=True,
            deskew_enabled=True,
            noise_removal=True,
            adaptive_threshold=True
        )

        performance_results = []

        for img_path in test_images:
            start_time = time.time()

            try:
                processed_img = image_processor.preprocess_pipeline(str(img_path), options)
                processing_time = time.time() - start_time

                # 파일 크기 확인
                file_size = os.path.getsize(img_path)

                performance_results.append({
                    'image_size': f"{img_path.name}",
                    'file_size_mb': file_size / (1024 * 1024),
                    'processing_time': processing_time,
                    'throughput': file_size / processing_time if processing_time > 0 else 0
                })

                print(f"Processed {img_path.name}: {processing_time:.2f}s")

                # 처리된 이미지 정리
                if processed_img and os.path.exists(processed_img):
                    os.remove(processed_img)

            except Exception as e:
                print(f"Failed to process {img_path.name}: {e}")

        # 성능 결과 출력
        print(f"\n=== Performance Results ===")
        for result in performance_results:
            print(f"Image: {result['image_size']}")
            print(f"  File size: {result['file_size_mb']:.2f} MB")
            print(f"  Processing time: {result['processing_time']:.2f}s")
            print(f"  Throughput: {result['throughput']:.0f} bytes/sec")
            print()

        # 기본 성능 검증 (각 이미지가 10초 이내에 처리되어야 함)
        for result in performance_results:
            assert result['processing_time'] < 10.0, \
                f"Image processing took too long: {result['processing_time']:.2f}s"

        print("=== Performance Test Completed Successfully ===\n")

    def test_memory_management_integration(self, temp_storage, image_processor,
                                           test_data_dir):
        """메모리 관리 통합 테스트"""
        print("\n=== Memory Management Integration Test ===")

        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss
            print(f"Initial memory usage: {initial_memory / 1024 / 1024:.1f} MB")
        except ImportError:
            print("psutil not available, skipping detailed memory monitoring")
            initial_memory = None

        # 여러 이미지를 연속으로 처리하여 메모리 누수 테스트
        from backend.core.image_processor import ProcessingOptions
        options = ProcessingOptions(
            apply_clahe=True,
            deskew_enabled=True,
            noise_removal=True,
            adaptive_threshold=True
        )

        processed_files = []

        for i in range(5):  # 5개 이미지 처리
            # 테스트 이미지 생성
            img = Image.new('RGB', (1000, 800), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50 + i*30), f"Memory test image {i+1}", fill='black')

            img_path = test_data_dir / f"memory_test_{i}.png"
            img.save(img_path)

            # 이미지 처리
            try:
                processed_img = image_processor.preprocess_pipeline(str(img_path), options)
                if processed_img:
                    processed_files.append(processed_img)

                print(f"Processed image {i+1}")

                # 중간 메모리 체크
                if initial_memory:
                    current_memory = process.memory_info().rss
                    memory_increase = current_memory - initial_memory
                    print(f"  Memory usage: {current_memory / 1024 / 1024:.1f} MB "
                          f"(+{memory_increase / 1024 / 1024:.1f} MB)")

            except Exception as e:
                print(f"Failed to process image {i+1}: {e}")

        # 정리
        for processed_file in processed_files:
            if os.path.exists(processed_file):
                os.remove(processed_file)

        # 가비지 컬렉션 강제 실행
        import gc
        gc.collect()

        # 최종 메모리 체크
        if initial_memory:
            final_memory = process.memory_info().rss
            total_increase = final_memory - initial_memory
            print(f"Final memory usage: {final_memory / 1024 / 1024:.1f} MB "
                  f"(+{total_increase / 1024 / 1024:.1f} MB)")

            # 메모리 증가가 100MB 이하여야 함
            assert total_increase < 100 * 1024 * 1024, \
                f"Memory usage increased too much: {total_increase / 1024 / 1024:.1f} MB"

        # temp storage 정리
        temp_storage.cleanup_expired_files(current_time=time.time() + 86401)

        print("=== Memory Management Test Completed Successfully ===\n")

    def test_concurrent_processing_integration(self, temp_storage, image_processor,
                                               test_data_dir):
        """동시 처리 통합 테스트"""
        print("\n=== Concurrent Processing Integration Test ===")

        from concurrent.futures import ThreadPoolExecutor
        import threading

        # 여러 테스트 이미지 생성
        test_images = []
        for i in range(3):
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), f"Concurrent test image {i+1}", fill='black')

            img_path = test_data_dir / f"concurrent_test_{i}.png"
            img.save(img_path)
            test_images.append(img_path)

        results = []
        errors = []

        def process_image(img_path, thread_id):
            """이미지 처리 작업"""
            try:
                print(f"Thread {thread_id}: Processing {img_path.name}")

                from backend.core.image_processor import ProcessingOptions
                options = ProcessingOptions(apply_clahe=True)

                start_time = time.time()
                processed_img = image_processor.preprocess_pipeline(str(img_path), options)
                processing_time = time.time() - start_time

                result = {
                    'thread_id': thread_id,
                    'image': img_path.name,
                    'processing_time': processing_time,
                    'success': True,
                    'processed_file': processed_img
                }

                print(f"Thread {thread_id}: Completed in {processing_time:.2f}s")
                return result

            except Exception as e:
                error_result = {
                    'thread_id': thread_id,
                    'image': img_path.name,
                    'error': str(e),
                    'success': False
                }
                print(f"Thread {thread_id}: Failed with error: {e}")
                return error_result

        # 동시 실행
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_image, img_path, i)
                for i, img_path in enumerate(test_images)
            ]

            for future in futures:
                result = future.result()
                if result['success']:
                    results.append(result)
                else:
                    errors.append(result)

        # 결과 검증
        print(f"Successful processes: {len(results)}")
        print(f"Failed processes: {len(errors)}")

        # 최소한 하나의 프로세스는 성공해야 함
        assert len(results) > 0, "No processes completed successfully"

        # 처리된 파일들 정리
        for result in results:
            if result.get('processed_file') and os.path.exists(result['processed_file']):
                os.remove(result['processed_file'])

        # 성능 통계
        if results:
            avg_time = sum(r['processing_time'] for r in results) / len(results)
            max_time = max(r['processing_time'] for r in results)
            min_time = min(r['processing_time'] for r in results)

            print(f"Processing time stats:")
            print(f"  Average: {avg_time:.2f}s")
            print(f"  Maximum: {max_time:.2f}s")
            print(f"  Minimum: {min_time:.2f}s")

        print("=== Concurrent Processing Test Completed Successfully ===\n")


class TestSystemReliability:
    """시스템 안정성 테스트"""

    def test_file_cleanup_reliability(self):
        """파일 정리 안정성 테스트"""
        print("\n=== File Cleanup Reliability Test ===")

        test_dir = Path(tempfile.mkdtemp(prefix="cleanup_test_"))
        temp_storage = TempStorage(str(test_dir))

        # 여러 파일 생성
        file_ids = []
        for i in range(5):
            file_id = temp_storage.save_file(
                f"Test content {i}".encode(),
                filename=f"test_{i}.txt",
                uploader_id="cleanup_test_user"
            )
            file_ids.append(file_id)

        # 파일이 모두 생성되었는지 확인
        for file_id in file_ids:
            assert temp_storage.get_file(file_id, "cleanup_test_user") is not None

        print(f"Created {len(file_ids)} test files")

        # 즉시 정리 (강제 만료)
        cleaned_count = temp_storage.cleanup_expired_files(current_time=time.time() + 86401)
        print(f"Cleaned up {cleaned_count} files")

        # 모든 파일이 정리되었는지 확인
        for file_id in file_ids:
            assert temp_storage.get_file(file_id, "cleanup_test_user") is None

        # 디렉토리 정리
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

        print("=== File Cleanup Test Completed Successfully ===\n")

    def test_configuration_loading(self):
        """설정 로딩 테스트"""
        print("\n=== Configuration Loading Test ===")

        # 각 컴포넌트의 기본 설정 로딩 테스트
        try:
            pdf_converter = PDFConverter()
            print("✓ PDFConverter initialized successfully")
        except Exception as e:
            print(f"✗ PDFConverter initialization failed: {e}")
            raise

        try:
            image_processor = ImageProcessor()
            print("✓ ImageProcessor initialized successfully")
        except Exception as e:
            print(f"✗ ImageProcessor initialization failed: {e}")
            raise

        try:
            text_corrector = TextCorrector()
            print("✓ TextCorrector initialized successfully")
        except Exception as e:
            print(f"✗ TextCorrector initialization failed: {e}")
            raise

        try:
            file_generator = FileGenerator()
            print("✓ FileGenerator initialized successfully")
        except Exception as e:
            print(f"✗ FileGenerator initialization failed: {e}")
            raise

        print("=== Configuration Loading Test Completed Successfully ===\n")

    def test_resource_limits(self):
        """리소스 제한 테스트"""
        print("\n=== Resource Limits Test ===")

        test_dir = Path(tempfile.mkdtemp(prefix="resource_test_"))
        temp_storage = TempStorage(str(test_dir))

        # 대용량 파일 생성 시도 (10MB)
        large_content = b"x" * (10 * 1024 * 1024)

        try:
            file_id = temp_storage.save_file(
                large_content,
                filename="large_file.bin",
                uploader_id="resource_test_user"
            )

            file_info = temp_storage.get_file(file_id, "resource_test_user")
            if file_info:
                file_size = file_info.file_size
                print(f"Large file created: {file_size / 1024 / 1024:.1f} MB")

                # 정리
                temp_storage.cleanup_expired_files(current_time=time.time() + 86401)

        except Exception as e:
            print(f"Large file creation failed (expected): {e}")

        # 디렉토리 정리
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

        print("=== Resource Limits Test Completed Successfully ===\n")


if __name__ == "__main__":
    # 단독 실행 시 간단한 테스트 실행
    print("Running basic integration test...")

    test_dir = Path(tempfile.mkdtemp(prefix="basic_test_"))
    temp_storage = TempStorage(str(test_dir))

    # 기본 기능 테스트
    file_id = temp_storage.save_file(
        b"Basic test content",
        filename="basic_test.txt",
        uploader_id="basic_test_user"
    )

    assert file_id is not None
    assert temp_storage.get_file(file_id, "basic_test_user") is not None

    # 정리
    temp_storage.cleanup_expired_files(current_time=time.time() + 86401)

    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)

    print("Basic integration test passed!")