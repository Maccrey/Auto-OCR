"""
PDFConverter 클래스 테스트
TDD 방식으로 PDF to PNG 변환 기능을 테스트합니다.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import io
from typing import List

from backend.core.pdf_converter import PDFConverter, ConversionError, PDFInfo


class TestPDFConverter:
    """PDFConverter 클래스 테스트 케이스"""
    
    @pytest.fixture
    def temp_dir(self):
        """테스트용 임시 디렉토리 생성"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def converter(self, temp_dir):
        """PDFConverter 인스턴스 생성"""
        return PDFConverter(output_dir=temp_dir, dpi=300)
    
    @pytest.fixture
    def sample_pdf_path(self, temp_dir):
        """샘플 PDF 파일 경로"""
        pdf_path = Path(temp_dir) / "sample.pdf"
        # 빈 PDF 파일 생성 (실제 테스트에서는 mock을 사용)
        pdf_path.write_bytes(b"%PDF-1.4\n")
        return str(pdf_path)
    
    def test_init_creates_output_directory(self, temp_dir):
        """PDFConverter 초기화 시 출력 디렉토리가 생성되는지 테스트"""
        output_dir = Path(temp_dir) / "output"
        converter = PDFConverter(output_dir=str(output_dir))
        
        assert output_dir.exists()
        assert output_dir.is_dir()
        assert converter.output_dir == output_dir
        assert converter.dpi == 200  # 기본값
    
    def test_init_with_custom_dpi(self, temp_dir):
        """커스텀 DPI로 초기화 테스트"""
        converter = PDFConverter(output_dir=temp_dir, dpi=300)
        
        assert converter.dpi == 300
    
    @patch('fitz.open')
    def test_validate_pdf_with_valid_file(self, mock_fitz_open, converter, sample_pdf_path):
        """유효한 PDF 파일 검증 테스트"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_doc.page_count = 5
        mock_doc.metadata = {'title': 'Test PDF', 'author': 'Test Author'}
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        is_valid = converter.validate_pdf(sample_pdf_path)
        
        assert is_valid is True
        mock_fitz_open.assert_called_once_with(sample_pdf_path)
    
    @patch('fitz.open')
    def test_validate_pdf_with_invalid_file(self, mock_fitz_open, converter):
        """잘못된 PDF 파일 검증 테스트"""
        mock_fitz_open.side_effect = Exception("Invalid PDF")
        
        is_valid = converter.validate_pdf("invalid.pdf")
        
        assert is_valid is False
    
    def test_validate_pdf_with_nonexistent_file(self, converter):
        """존재하지 않는 파일 검증 테스트"""
        is_valid = converter.validate_pdf("nonexistent.pdf")
        
        assert is_valid is False
    
    @patch('fitz.open')
    def test_get_pdf_info_returns_correct_data(self, mock_fitz_open, converter, sample_pdf_path):
        """PDF 정보 반환 테스트"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_doc.page_count = 3
        mock_doc.metadata = {
            'title': 'Test Document',
            'author': 'Test Author',
            'subject': 'Test Subject'
        }
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        pdf_info = converter.get_pdf_info(sample_pdf_path)
        
        assert pdf_info is not None
        assert pdf_info.page_count == 3
        assert pdf_info.title == 'Test Document'
        assert pdf_info.author == 'Test Author'
        assert pdf_info.subject == 'Test Subject'
        assert isinstance(pdf_info.file_size, int)
        assert pdf_info.file_size > 0
    
    @patch('fitz.open')
    def test_get_pdf_info_with_invalid_file(self, mock_fitz_open, converter):
        """잘못된 PDF 파일의 정보 요청 테스트"""
        mock_fitz_open.side_effect = Exception("Invalid PDF")
        
        pdf_info = converter.get_pdf_info("invalid.pdf")
        
        assert pdf_info is None
    
    @patch('fitz.open')
    def test_convert_pdf_to_png_single_page(self, mock_fitz_open, converter, sample_pdf_path):
        """단일 페이지 PDF 변환 테스트"""
        # Mock PDF document and page
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.pil_tobytes.return_value = b"fake_png_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_doc.__getitem__ = lambda x, i: mock_page
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        # Mock file writing
        with patch('builtins.open', mock_open()) as mock_file:
            image_paths = converter.convert_pdf_to_png(sample_pdf_path)
        
        assert len(image_paths) == 1
        assert isinstance(image_paths[0], str)
        assert image_paths[0].endswith('.png')
        mock_page.get_pixmap.assert_called_once()
    
    @patch('fitz.open')
    def test_convert_pdf_to_png_multiple_pages(self, mock_fitz_open, converter, sample_pdf_path):
        """다중 페이지 PDF 변환 테스트"""
        # Mock PDF document and pages
        mock_pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_pixmap = MagicMock()
            mock_pixmap.pil_tobytes.return_value = f"fake_png_data_{i}".encode()
            mock_page.get_pixmap.return_value = mock_pixmap
            mock_pages.append(mock_page)
        
        mock_doc = MagicMock()
        mock_doc.page_count = 3
        mock_doc.__iter__ = lambda x: iter(mock_pages)
        mock_doc.__getitem__ = lambda x, i: mock_pages[i]
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        # Mock file writing
        with patch('builtins.open', mock_open()) as mock_file:
            image_paths = converter.convert_pdf_to_png(sample_pdf_path)
        
        assert len(image_paths) == 3
        for i, path in enumerate(image_paths):
            assert path.endswith(f'_page_{i+1}.png')
        
        # 각 페이지에 대해 get_pixmap이 호출되었는지 확인
        for mock_page in mock_pages:
            mock_page.get_pixmap.assert_called_once()
    
    @patch('fitz.open')
    def test_convert_pdf_to_png_with_invalid_pdf(self, mock_fitz_open, converter):
        """잘못된 PDF 변환 시 오류 발생 테스트"""
        mock_fitz_open.side_effect = Exception("Cannot open PDF")
        
        with pytest.raises(ConversionError):
            converter.convert_pdf_to_png("invalid.pdf")
    
    def test_convert_pdf_to_png_with_nonexistent_file(self, converter):
        """존재하지 않는 파일 변환 시 오류 발생 테스트"""
        with pytest.raises(ConversionError):
            converter.convert_pdf_to_png("nonexistent.pdf")
    
    @patch('fitz.open')
    def test_estimate_processing_time_returns_reasonable_value(self, mock_fitz_open, converter, sample_pdf_path):
        """처리 시간 추정 테스트"""
        mock_doc = MagicMock()
        mock_doc.page_count = 10
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        estimated_time = converter.estimate_processing_time(sample_pdf_path)
        
        assert isinstance(estimated_time, float)
        assert estimated_time > 0
        # 10페이지 기준 합리적인 시간 (페이지당 1-5초 정도)
        assert 10 <= estimated_time <= 50
    
    @patch('fitz.open')
    def test_estimate_processing_time_with_invalid_pdf(self, mock_fitz_open, converter):
        """잘못된 PDF의 처리 시간 추정 테스트"""
        mock_fitz_open.side_effect = Exception("Invalid PDF")
        
        estimated_time = converter.estimate_processing_time("invalid.pdf")
        
        assert estimated_time == 0.0
    
    def test_get_output_filename_generation(self, converter):
        """출력 파일명 생성 테스트"""
        pdf_path = "/path/to/document.pdf"
        
        # 단일 페이지
        filename = converter._get_output_filename(pdf_path, 0, 1)
        assert filename == "document.png"
        
        # 다중 페이지
        filename = converter._get_output_filename(pdf_path, 0, 5)
        assert filename == "document_page_1.png"
        
        filename = converter._get_output_filename(pdf_path, 2, 5)
        assert filename == "document_page_3.png"
    
    @patch('fitz.open')
    def test_convert_with_custom_dpi(self, mock_fitz_open, converter, sample_pdf_path):
        """커스텀 DPI로 변환 테스트"""
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.pil_tobytes.return_value = b"fake_png_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_doc.__getitem__ = lambda x, i: mock_page
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        # DPI 설정이 get_pixmap에 전달되는지 확인
        with patch('builtins.open', mock_open()):
            converter.convert_pdf_to_png(sample_pdf_path)
        
        # matrix 인자가 DPI 설정과 함께 호출되었는지 확인
        mock_page.get_pixmap.assert_called_once()
        call_args = mock_page.get_pixmap.call_args
        assert 'matrix' in call_args.kwargs or len(call_args.args) > 0
    
    def test_conversion_error_message(self):
        """ConversionError 메시지 테스트"""
        error_msg = "Test error message"
        error = ConversionError(error_msg)
        
        assert str(error) == error_msg
        assert isinstance(error, Exception)
    
    def test_pdf_info_dataclass_structure(self):
        """PDFInfo 데이터 클래스 구조 테스트"""
        pdf_info = PDFInfo(
            page_count=5,
            title="Test Title",
            author="Test Author",
            subject="Test Subject",
            file_size=1024
        )
        
        assert pdf_info.page_count == 5
        assert pdf_info.title == "Test Title"
        assert pdf_info.author == "Test Author"
        assert pdf_info.subject == "Test Subject"
        assert pdf_info.file_size == 1024
    
    @patch('fitz.open')
    def test_concurrent_conversions_succeed(self, mock_fitz_open, converter, temp_dir):
        """동시 변환 작업 테스트"""
        import threading
        
        # Mock setup
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.pil_tobytes.return_value = b"fake_png_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_doc.__iter__ = lambda x: iter([mock_page])
        mock_fitz_open.return_value = mock_doc
        
        results = []
        errors = []
        
        def convert_worker(file_id):
            try:
                pdf_path = Path(temp_dir) / f"test_{file_id}.pdf"
                pdf_path.write_bytes(b"%PDF-1.4\n")
                
                with patch('builtins.open', mock_open()):
                    image_paths = converter.convert_pdf_to_png(str(pdf_path))
                results.append(image_paths)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=convert_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 5
        for result in results:
            assert len(result) == 1  # 각각 1페이지
    
    @patch('fitz.open')
    def test_large_pdf_handling(self, mock_fitz_open, converter, sample_pdf_path):
        """대용량 PDF 처리 테스트"""
        # 100페이지 PDF 시뮬레이션
        mock_pages = []
        for i in range(100):
            mock_page = MagicMock()
            mock_pixmap = MagicMock()
            mock_pixmap.pil_tobytes.return_value = f"fake_png_data_{i}".encode()
            mock_page.get_pixmap.return_value = mock_pixmap
            mock_pages.append(mock_page)
        
        mock_doc = MagicMock()
        mock_doc.page_count = 100
        mock_doc.__iter__ = lambda x: iter(mock_pages)
        mock_doc.__getitem__ = lambda x, i: mock_pages[i]
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=None)
        mock_fitz_open.return_value = mock_doc
        
        with patch('builtins.open', mock_open()):
            image_paths = converter.convert_pdf_to_png(sample_pdf_path)
        
        assert len(image_paths) == 100
        # 모든 경로가 올바른 형식인지 확인
        for i, path in enumerate(image_paths):
            assert path.endswith(f'_page_{i+1}.png')