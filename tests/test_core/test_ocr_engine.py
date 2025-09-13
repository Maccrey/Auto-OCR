"""
OCREngine 클래스 테스트 모듈

이 모듈은 OCR 엔진들의 기능을 테스트합니다:
- PaddleOCR 엔진 기능 테스트
- Tesseract 엔진 기능 테스트
- 앙상블 기능 테스트
- 오류 처리 테스트
"""

import pytest
import numpy as np
from PIL import Image
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

# Import from actual module
from backend.core.ocr_engine import BoundingBox, OCRResult

class TestOCREngineBase:
    """OCR 엔진 베이스 클래스 테스트"""
    
    def test_ocr_engine_interface(self):
        """OCR 엔진 인터페이스 정의 테스트"""
        # OCREngine 베이스 클래스가 올바른 인터페이스를 가지는지 확인
        from backend.core.ocr_engine import OCREngine
        
        # 추상 클래스이므로 직접 인스턴스화 불가능
        with pytest.raises(TypeError):
            OCREngine()

class TestPaddleOCREngine:
    """PaddleOCR 엔진 테스트"""
    
    @pytest.fixture
    def mock_paddle_ocr(self):
        """PaddleOCR 모킹"""
        # PaddleOCR 모듈 자체를 모킹
        mock_paddleocr = Mock()
        mock_paddleocr_instance = Mock()
        mock_paddleocr_instance.ocr.return_value = [
            [
                [[[10, 10], [100, 10], [100, 30], [10, 30]], ('안녕하세요', 0.95)],
                [[[10, 40], [120, 40], [120, 60], [10, 60]], ('테스트입니다', 0.92)]
            ]
        ]
        mock_paddleocr.PaddleOCR.return_value = mock_paddleocr_instance
        
        with patch.dict('sys.modules', {'paddleocr': mock_paddleocr}):
            yield mock_paddleocr_instance
    
    @pytest.fixture
    def test_image(self):
        """테스트용 이미지 생성"""
        # 간단한 테스트 이미지 생성 (100x100 흰색 배경)
        image = Image.new('RGB', (100, 100), color='white')
        return image
    
    def test_paddle_ocr_engine_initialization(self, mock_paddle_ocr):
        """PaddleOCR 엔진 초기화 테스트"""
        from backend.core.ocr_engine import PaddleOCREngine
        
        engine = PaddleOCREngine()
        assert engine.engine_name == "PaddleOCR"
        assert engine.language == "korean"
        assert engine.use_gpu is False
    
    def test_paddle_ocr_engine_initialization_with_gpu(self, mock_paddle_ocr):
        """GPU 사용 PaddleOCR 엔진 초기화 테스트"""
        from backend.core.ocr_engine import PaddleOCREngine
        
        engine = PaddleOCREngine(use_gpu=True)
        assert engine.use_gpu is True
    
    def test_paddle_ocr_text_recognition_success(self, mock_paddle_ocr, test_image):
        """PaddleOCR 텍스트 인식 성공 테스트"""
        from backend.core.ocr_engine import PaddleOCREngine
        
        engine = PaddleOCREngine()
        result = engine.recognize_text(test_image)
        
        assert isinstance(result, OCRResult)
        assert result.text == "안녕하세요\n테스트입니다"
        assert result.engine_used == "PaddleOCR"
        assert result.confidence > 0.9
        assert len(result.line_boxes) == 2
    
    def test_paddle_ocr_confidence_calculation(self, mock_paddle_ocr, test_image):
        """PaddleOCR 신뢰도 점수 계산 테스트"""
        from backend.core.ocr_engine import PaddleOCREngine
        
        engine = PaddleOCREngine()
        result = engine.recognize_text(test_image)
        
        # 예상 신뢰도: (0.95 + 0.92) / 2 = 0.935
        expected_confidence = (0.95 + 0.92) / 2
        assert abs(result.confidence - expected_confidence) < 0.01
    
    def test_paddle_ocr_empty_result_handling(self, test_image):
        """PaddleOCR 빈 결과 처리 테스트"""
        from backend.core.ocr_engine import PaddleOCREngine
        
        # PaddleOCR 빈 결과 모킹
        mock_paddleocr = Mock()
        mock_paddleocr_instance = Mock()
        mock_paddleocr_instance.ocr.return_value = [[]]  # 빈 결과
        mock_paddleocr.PaddleOCR.return_value = mock_paddleocr_instance
        
        with patch.dict('sys.modules', {'paddleocr': mock_paddleocr}):
            engine = PaddleOCREngine()
            result = engine.recognize_text(test_image)
            
            assert result.text == ""
            assert result.confidence == 0.0
            assert len(result.line_boxes) == 0
    
    def test_paddle_ocr_error_handling(self, test_image):
        """PaddleOCR 오류 처리 테스트"""
        from backend.core.ocr_engine import PaddleOCREngine, OCREngineError
        
        # PaddleOCR 오류 모킹
        mock_paddleocr = Mock()
        mock_paddleocr_instance = Mock()
        mock_paddleocr_instance.ocr.side_effect = Exception("PaddleOCR error")
        mock_paddleocr.PaddleOCR.return_value = mock_paddleocr_instance
        
        with patch.dict('sys.modules', {'paddleocr': mock_paddleocr}):
            engine = PaddleOCREngine()
            
            with pytest.raises(OCREngineError):
                engine.recognize_text(test_image)

class TestTesseractEngine:
    """Tesseract 엔진 테스트"""
    
    @pytest.fixture
    def mock_tesseract(self):
        """Tesseract 모킹"""
        # pytesseract 모듈 자체를 모킹
        mock_pytesseract = Mock()
        mock_pytesseract.image_to_string.return_value = "안녕하세요\n테스트입니다"
        mock_pytesseract.image_to_data.return_value = {
            'level': [1, 2, 3, 4, 5],
            'page_num': [1, 1, 1, 1, 1],
            'block_num': [0, 1, 1, 1, 1],
            'par_num': [0, 0, 1, 1, 1],
            'line_num': [0, 0, 0, 1, 2],
            'word_num': [0, 0, 0, 1, 1],
            'left': [0, 10, 10, 10, 10],
            'top': [0, 10, 10, 10, 40],
            'width': [100, 90, 90, 90, 110],
            'height': [100, 50, 50, 20, 20],
            'conf': ['-1', '-1', '-1', '95', '92'],
            'text': ['', '', '', '안녕하세요', '테스트입니다']
        }
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.get_languages.return_value = ["eng", "kor"]
        mock_pytesseract.Output = Mock()
        mock_pytesseract.Output.DICT = 'dict'
        
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract}):
            yield mock_pytesseract
    
    @pytest.fixture
    def test_image(self):
        """테스트용 이미지 생성"""
        image = Image.new('RGB', (100, 100), color='white')
        return image
    
    def test_tesseract_engine_initialization(self, mock_tesseract):
        """Tesseract 엔진 초기화 테스트"""
        from backend.core.ocr_engine import TesseractEngine
        
        engine = TesseractEngine()
        assert engine.engine_name == "Tesseract"
        assert engine.language == "kor"
    
    def test_tesseract_custom_language(self, mock_tesseract):
        """Tesseract 사용자 정의 언어 설정 테스트"""
        from backend.core.ocr_engine import TesseractEngine
        
        engine = TesseractEngine(language="kor+eng")
        assert engine.language == "kor+eng"
    
    def test_tesseract_text_recognition_success(self, mock_tesseract, test_image):
        """Tesseract 텍스트 인식 성공 테스트"""
        from backend.core.ocr_engine import TesseractEngine
        
        engine = TesseractEngine()
        result = engine.recognize_text(test_image)
        
        assert isinstance(result, OCRResult)
        assert result.text == "안녕하세요\n테스트입니다"
        assert result.engine_used == "Tesseract"
        assert result.confidence > 0.9
        assert len(result.line_boxes) == 2
    
    def test_tesseract_confidence_calculation(self, mock_tesseract, test_image):
        """Tesseract 신뢰도 점수 계산 테스트"""
        from backend.core.ocr_engine import TesseractEngine
        
        engine = TesseractEngine()
        result = engine.recognize_text(test_image)
        
        # 예상 신뢰도: (95 + 92) / 2 / 100 = 0.935
        expected_confidence = (95 + 92) / 2 / 100
        assert abs(result.confidence - expected_confidence) < 0.01
    
    def test_tesseract_error_handling(self, test_image):
        """Tesseract 오류 처리 테스트"""
        from backend.core.ocr_engine import TesseractEngine, OCREngineError
        
        # pytesseract 오류 모킹
        mock_pytesseract = Mock()
        mock_pytesseract.image_to_string.side_effect = Exception("Tesseract error")
        mock_pytesseract.get_tesseract_version.return_value = "5.0.0"
        mock_pytesseract.get_languages.return_value = ["eng", "kor"]
        
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract}):
            engine = TesseractEngine()
            
            with pytest.raises(OCREngineError):
                engine.recognize_text(test_image)

class TestOCREngineManager:
    """OCR 엔진 매니저 테스트"""
    
    @pytest.fixture
    def mock_engines(self):
        """모킹된 OCR 엔진들"""
        with patch('backend.core.ocr_engine.PaddleOCREngine') as mock_paddle, \
             patch('backend.core.ocr_engine.TesseractEngine') as mock_tesseract:
            
            # PaddleOCR 모킹
            paddle_instance = Mock()
            paddle_result = OCRResult(
                text="안녕하세요",
                confidence=0.95,
                line_boxes=[BoundingBox(10, 10, 90, 20, 0.95)],
                engine_used="PaddleOCR"
            )
            paddle_instance.recognize_text.return_value = paddle_result
            mock_paddle.return_value = paddle_instance
            
            # Tesseract 모킹
            tesseract_instance = Mock()
            tesseract_result = OCRResult(
                text="안녕하세요",
                confidence=0.85,
                line_boxes=[BoundingBox(10, 10, 90, 20, 0.85)],
                engine_used="Tesseract"
            )
            tesseract_instance.recognize_text.return_value = tesseract_result
            mock_tesseract.return_value = tesseract_instance
            
            yield paddle_instance, tesseract_instance
    
    @pytest.fixture
    def test_image(self):
        """테스트용 이미지"""
        return Image.new('RGB', (100, 100), color='white')
    
    def test_ocr_engine_manager_initialization(self, mock_engines):
        """OCR 엔진 매니저 초기화 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        manager = OCREngineManager()
        assert "paddle" in manager.available_engines
        assert "tesseract" in manager.available_engines
        assert manager.default_engine == "paddle"
    
    def test_set_engine_success(self, mock_engines):
        """엔진 설정 성공 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        manager = OCREngineManager()
        manager.set_engine("tesseract")
        assert manager.current_engine == "tesseract"
    
    def test_set_engine_invalid(self, mock_engines):
        """잘못된 엔진 설정 테스트"""
        from backend.core.ocr_engine import OCREngineManager, OCREngineError
        
        manager = OCREngineManager()
        
        with pytest.raises(OCREngineError):
            manager.set_engine("invalid_engine")
    
    def test_recognize_text_with_current_engine(self, mock_engines, test_image):
        """현재 엔진으로 텍스트 인식 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        manager = OCREngineManager()
        result = manager.recognize_text(test_image)
        
        assert isinstance(result, OCRResult)
        assert result.engine_used == "PaddleOCR"
        assert result.text == "안녕하세요"
    
    def test_ensemble_recognition(self, mock_engines, test_image):
        """앙상블 인식 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        manager = OCREngineManager()
        result = manager.ensemble_recognition(test_image, ["paddle", "tesseract"])
        
        assert isinstance(result, OCRResult)
        assert result.engine_used == "Ensemble(paddle,tesseract)"
        # 더 높은 신뢰도를 가진 PaddleOCR 결과가 선택되어야 함
        assert result.confidence == 0.95
    
    def test_ensemble_recognition_weighted_average(self, mock_engines, test_image):
        """앙상블 인식 가중 평균 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        # 같은 텍스트를 반환하도록 설정
        paddle_engine, tesseract_engine = mock_engines
        paddle_engine.recognize_text.return_value.text = "동일한텍스트"
        tesseract_engine.recognize_text.return_value.text = "동일한텍스트"
        
        manager = OCREngineManager()
        result = manager.ensemble_recognition(
            test_image, 
            ["paddle", "tesseract"], 
            strategy="weighted_average"
        )
        
        # 가중 평균 신뢰도: (0.95 + 0.85) / 2 = 0.90
        expected_confidence = (0.95 + 0.85) / 2
        assert abs(result.confidence - expected_confidence) < 0.01
    
    def test_get_confidence_scores(self, mock_engines, test_image):
        """신뢰도 점수 반환 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        manager = OCREngineManager()
        
        # 여러 엔진으로 인식 실행
        manager.recognize_text(test_image)  # PaddleOCR
        manager.set_engine("tesseract")
        manager.recognize_text(test_image)  # Tesseract
        
        scores = manager.get_confidence_scores()
        
        assert "paddle" in scores
        assert "tesseract" in scores
        assert scores["paddle"] == 0.95
        assert scores["tesseract"] == 0.85
    
    def test_engine_performance_tracking(self, mock_engines, test_image):
        """엔진 성능 추적 테스트"""
        from backend.core.ocr_engine import OCREngineManager
        
        manager = OCREngineManager()
        
        # 처리 시간 모킹
        paddle_engine, tesseract_engine = mock_engines
        paddle_engine.recognize_text.return_value.processing_time = 1.5
        tesseract_engine.recognize_text.return_value.processing_time = 2.3
        
        # 각 엔진으로 인식 실행
        result1 = manager.recognize_text(test_image)
        manager.set_engine("tesseract")
        result2 = manager.recognize_text(test_image)
        
        performance = manager.get_performance_stats()
        
        assert "paddle" in performance
        assert "tesseract" in performance
        assert performance["paddle"]["avg_time"] == 1.5
        assert performance["tesseract"]["avg_time"] == 2.3

class TestOCREngineIntegration:
    """OCR 엔진 통합 테스트"""
    
    def test_real_image_processing_pipeline(self):
        """실제 이미지 처리 파이프라인 테스트"""
        # 실제 테스트 이미지가 있는 경우에만 실행
        test_image_path = Path("tests/resources/test_korean_text.png")
        
        if not test_image_path.exists():
            pytest.skip("Test image not found")
        
        from backend.core.ocr_engine import OCREngineManager
        
        # 실제 이미지로 테스트
        image = Image.open(test_image_path)
        manager = OCREngineManager()
        
        result = manager.recognize_text(image)
        
        assert isinstance(result, OCRResult)
        assert len(result.text) > 0
        assert result.confidence > 0.0
        assert len(result.line_boxes) > 0
    
    def test_multiple_engines_consistency(self):
        """여러 엔진 결과 일관성 테스트"""
        test_image_path = Path("tests/resources/simple_korean_text.png")
        
        if not test_image_path.exists():
            pytest.skip("Test image not found")
        
        from backend.core.ocr_engine import OCREngineManager
        
        image = Image.open(test_image_path)
        manager = OCREngineManager()
        
        # PaddleOCR 결과
        paddle_result = manager.recognize_text(image)
        
        # Tesseract 결과
        manager.set_engine("tesseract")
        tesseract_result = manager.recognize_text(image)
        
        # 앙상블 결과
        ensemble_result = manager.ensemble_recognition(image, ["paddle", "tesseract"])
        
        # 결과가 모두 유효한지 확인
        for result in [paddle_result, tesseract_result, ensemble_result]:
            assert isinstance(result, OCRResult)
            assert result.confidence >= 0.0
            assert isinstance(result.text, str)