"""
OCR 엔진 모듈

이 모듈은 다양한 OCR 엔진들을 통합 관리합니다:
- PaddleOCR: 한국어 지원이 우수한 메인 OCR 엔진
- Tesseract: 범용 OCR 엔진
- 앙상블 기능: 여러 엔진 결과를 조합하여 정확도 향상
"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple, Any
from PIL import Image
import numpy as np
from pathlib import Path

# 로깅 설정
logger = logging.getLogger(__name__)


class OCREngineError(Exception):
    """OCR 엔진 관련 오류"""
    pass


@dataclass
class BoundingBox:
    """바운딩 박스 정보"""
    x: int
    y: int
    width: int
    height: int
    confidence: float

    def __post_init__(self):
        """초기화 후 검증"""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class OCRResult:
    """OCR 결과 데이터 클래스"""
    text: str
    confidence: float
    line_boxes: List[BoundingBox]
    engine_used: str
    processing_time: float = 0.0

    def __post_init__(self):
        """초기화 후 검증"""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.processing_time < 0.0:
            raise ValueError("Processing time must be non-negative")


class OCREngine(ABC):
    """OCR 엔진 베이스 클래스"""
    
    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self._is_initialized = False
        self._initialization_error = None
    
    @abstractmethod
    def _initialize_engine(self) -> None:
        """엔진 초기화 (하위 클래스에서 구현)"""
        pass
    
    @abstractmethod
    def _recognize_text_impl(self, image: Image.Image) -> OCRResult:
        """텍스트 인식 구현 (하위 클래스에서 구현)"""
        pass
    
    def initialize(self) -> None:
        """엔진 초기화"""
        if self._is_initialized:
            return
        
        try:
            self._initialize_engine()
            self._is_initialized = True
            logger.info(f"{self.engine_name} engine initialized successfully")
        except Exception as e:
            self._initialization_error = e
            logger.error(f"Failed to initialize {self.engine_name} engine: {e}")
            raise OCREngineError(f"Failed to initialize {self.engine_name}: {e}")
    
    def recognize_text(self, image: Union[Image.Image, np.ndarray, str, Path]) -> OCRResult:
        """
        이미지에서 텍스트 인식
        
        Args:
            image: PIL Image, numpy array, 또는 이미지 파일 경로
            
        Returns:
            OCRResult: 인식 결과
            
        Raises:
            OCREngineError: 인식 실패 시
        """
        # 엔진 초기화 확인
        if not self._is_initialized:
            self.initialize()
        
        # 이미지 전처리
        processed_image = self._preprocess_image(image)
        
        # 처리 시간 측정
        start_time = time.time()
        
        try:
            result = self._recognize_text_impl(processed_image)
            result.processing_time = time.time() - start_time
            result.engine_used = self.engine_name
            
            logger.debug(f"{self.engine_name} recognition completed in {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"{self.engine_name} recognition failed after {processing_time:.2f}s: {e}")
            raise OCREngineError(f"{self.engine_name} recognition failed: {e}")
    
    def _preprocess_image(self, image: Union[Image.Image, np.ndarray, str, Path]) -> Image.Image:
        """이미지 전처리"""
        if isinstance(image, (str, Path)):
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        elif not isinstance(image, Image.Image):
            raise ValueError(f"Unsupported image type: {type(image)}")
        
        # RGB 변환
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image


class PaddleOCREngine(OCREngine):
    """PaddleOCR 엔진 구현"""
    
    def __init__(self, use_gpu: bool = False, language: str = "korean"):
        super().__init__("PaddleOCR")
        self.use_gpu = use_gpu
        self.language = language
        self.ocr_engine = None
    
    def _initialize_engine(self) -> None:
        """PaddleOCR 엔진 초기화"""
        try:
            import paddleocr
            
            # PaddleOCR 초기화
            self.ocr_engine = paddleocr.PaddleOCR(
                use_angle_cls=True,
                lang=self.language,
                use_gpu=self.use_gpu,
                show_log=False
            )
            
        except ImportError:
            raise OCREngineError("PaddleOCR is not installed. Please install with: pip install paddleocr")
        except Exception as e:
            raise OCREngineError(f"Failed to initialize PaddleOCR: {e}")
    
    def _recognize_text_impl(self, image: Image.Image) -> OCRResult:
        """PaddleOCR로 텍스트 인식 구현"""
        try:
            # PIL Image를 numpy array로 변환
            image_array = np.array(image)
            
            # PaddleOCR 실행
            result = self.ocr_engine.ocr(image_array, cls=True)
            
            # 결과 파싱
            return self._parse_paddle_result(result)
            
        except Exception as e:
            raise OCREngineError(f"PaddleOCR recognition failed: {e}")
    
    def _parse_paddle_result(self, paddle_result: List) -> OCRResult:
        """PaddleOCR 결과 파싱"""
        if not paddle_result or not paddle_result[0]:
            return OCRResult(
                text="",
                confidence=0.0,
                line_boxes=[],
                engine_used=self.engine_name
            )
        
        lines = []
        confidences = []
        line_boxes = []
        
        for line in paddle_result[0]:
            if len(line) >= 2:
                box = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)
                
                if isinstance(text_info, tuple) and len(text_info) >= 2:
                    text, confidence = text_info
                    lines.append(text)
                    confidences.append(confidence)
                    
                    # 바운딩 박스 계산
                    if len(box) >= 4:
                        x_coords = [point[0] for point in box]
                        y_coords = [point[1] for point in box]
                        
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)
                        
                        bbox = BoundingBox(
                            x=int(x_min),
                            y=int(y_min),
                            width=int(x_max - x_min),
                            height=int(y_max - y_min),
                            confidence=confidence
                        )
                        line_boxes.append(bbox)
        
        # 전체 텍스트 및 평균 신뢰도 계산
        full_text = "\n".join(lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            line_boxes=line_boxes,
            engine_used=self.engine_name
        )


class TesseractEngine(OCREngine):
    """Tesseract 엔진 구현"""
    
    def __init__(self, language: str = "kor"):
        super().__init__("Tesseract")
        self.language = language
        self.custom_config = r'--oem 3 --psm 6'
    
    def _initialize_engine(self) -> None:
        """Tesseract 엔진 초기화"""
        try:
            import pytesseract
            
            # Tesseract 설치 확인
            pytesseract.get_tesseract_version()
            
            # 한국어 모델 확인
            available_langs = pytesseract.get_languages(config='')
            if 'kor' not in available_langs and 'kor' in self.language:
                logger.warning("Korean language model not found. Results may be inaccurate.")
            
        except ImportError:
            raise OCREngineError("Pytesseract is not installed. Please install with: pip install pytesseract")
        except pytesseract.TesseractNotFoundError:
            raise OCREngineError("Tesseract executable not found. Please install Tesseract OCR.")
        except Exception as e:
            raise OCREngineError(f"Failed to initialize Tesseract: {e}")
    
    def _recognize_text_impl(self, image: Image.Image) -> OCRResult:
        """Tesseract로 텍스트 인식 구현"""
        try:
            import pytesseract
            
            # 텍스트 추출
            text = pytesseract.image_to_string(
                image,
                lang=self.language,
                config=self.custom_config
            ).strip()
            
            # 상세 정보 추출
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                config=self.custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # 결과 파싱
            return self._parse_tesseract_result(text, data)
            
        except Exception as e:
            raise OCREngineError(f"Tesseract recognition failed: {e}")
    
    def _parse_tesseract_result(self, text: str, data: Dict) -> OCRResult:
        """Tesseract 결과 파싱"""
        if not text:
            return OCRResult(
                text="",
                confidence=0.0,
                line_boxes=[],
                engine_used=self.engine_name
            )
        
        # 라인별 바운딩 박스 및 신뢰도 추출
        line_boxes = []
        confidences = []
        
        # 라인 레벨 정보 추출 (level 4 = word level)
        current_line = -1
        line_words = []
        line_confidences = []
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0:  # 유효한 신뢰도만
                conf = int(data['conf'][i])
                word = data['text'][i].strip()
                
                if word:  # 빈 텍스트가 아닌 경우
                    line_num = data['line_num'][i]
                    
                    # 새로운 라인 시작
                    if line_num != current_line:
                        # 이전 라인 처리
                        if line_words and line_confidences:
                            self._add_line_box(line_words, line_confidences, line_boxes, data, i-len(line_words))
                        
                        # 새 라인 시작
                        current_line = line_num
                        line_words = [word]
                        line_confidences = [conf]
                    else:
                        line_words.append(word)
                        line_confidences.append(conf)
                    
                    confidences.append(conf / 100.0)  # 0-1 범위로 정규화
        
        # 마지막 라인 처리
        if line_words and line_confidences:
            self._add_line_box(line_words, line_confidences, line_boxes, data, len(data['text']) - len(line_words))
        
        # 평균 신뢰도 계산
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return OCRResult(
            text=text,
            confidence=avg_confidence,
            line_boxes=line_boxes,
            engine_used=self.engine_name
        )
    
    def _add_line_box(self, words: List[str], confidences: List[int], 
                      line_boxes: List[BoundingBox], data: Dict, start_idx: int) -> None:
        """라인 바운딩 박스 추가"""
        if not words or not confidences:
            return
        
        # 라인의 전체 바운딩 박스 계산
        x_coords = []
        y_coords = []
        
        for i in range(len(words)):
            idx = start_idx + i
            if idx < len(data['left']):
                x_coords.extend([data['left'][idx], data['left'][idx] + data['width'][idx]])
                y_coords.extend([data['top'][idx], data['top'][idx] + data['height'][idx]])
        
        if x_coords and y_coords:
            avg_confidence = sum(confidences) / len(confidences) / 100.0
            
            bbox = BoundingBox(
                x=min(x_coords),
                y=min(y_coords),
                width=max(x_coords) - min(x_coords),
                height=max(y_coords) - min(y_coords),
                confidence=avg_confidence
            )
            line_boxes.append(bbox)


class OCREngineManager:
    """OCR 엔진 매니저 클래스"""
    
    def __init__(self):
        self.engines: Dict[str, OCREngine] = {}
        self.available_engines = ["paddle", "tesseract"]
        self.default_engine = "paddle"
        self.current_engine = self.default_engine
        self._confidence_history: Dict[str, List[float]] = {}
        self._performance_history: Dict[str, List[float]] = {}
        
        # 엔진 인스턴스 생성
        self._initialize_engines()
    
    def _initialize_engines(self) -> None:
        """사용 가능한 엔진들 초기화"""
        try:
            self.engines["paddle"] = PaddleOCREngine()
        except Exception as e:
            logger.warning(f"PaddleOCR engine not available: {e}")
            if "paddle" in self.available_engines:
                self.available_engines.remove("paddle")
        
        try:
            self.engines["tesseract"] = TesseractEngine()
        except Exception as e:
            logger.warning(f"Tesseract engine not available: {e}")
            if "tesseract" in self.available_engines:
                self.available_engines.remove("tesseract")
        
        if not self.available_engines:
            raise OCREngineError("No OCR engines available")
        
        # 기본 엔진 재설정 (필요시)
        if self.default_engine not in self.available_engines:
            self.default_engine = self.available_engines[0]
            self.current_engine = self.default_engine
    
    def set_engine(self, engine_name: str) -> None:
        """현재 사용할 엔진 설정"""
        if engine_name not in self.available_engines:
            raise OCREngineError(f"Engine '{engine_name}' not available. Available engines: {self.available_engines}")
        
        self.current_engine = engine_name
        logger.info(f"OCR engine set to: {engine_name}")
    
    def recognize_text(self, image: Union[Image.Image, np.ndarray, str, Path]) -> OCRResult:
        """현재 설정된 엔진으로 텍스트 인식"""
        engine = self.engines[self.current_engine]
        result = engine.recognize_text(image)
        
        # 성능 통계 업데이트
        self._update_statistics(self.current_engine, result)
        
        return result
    
    def ensemble_recognition(self, 
                           image: Union[Image.Image, np.ndarray, str, Path],
                           engines: List[str],
                           strategy: str = "best_confidence") -> OCRResult:
        """
        여러 엔진을 사용한 앙상블 인식
        
        Args:
            image: 입력 이미지
            engines: 사용할 엔진 목록
            strategy: 앙상블 전략 ("best_confidence", "weighted_average", "voting")
            
        Returns:
            OCRResult: 앙상블 결과
        """
        if not engines:
            raise OCREngineError("No engines specified for ensemble")
        
        # 유효한 엔진만 필터링
        valid_engines = [eng for eng in engines if eng in self.available_engines]
        if not valid_engines:
            raise OCREngineError(f"None of the specified engines are available: {engines}")
        
        # 각 엔진으로 인식 실행
        results = []
        for engine_name in valid_engines:
            try:
                engine = self.engines[engine_name]
                result = engine.recognize_text(image)
                results.append(result)
                
                # 통계 업데이트
                self._update_statistics(engine_name, result)
                
            except Exception as e:
                logger.warning(f"Engine {engine_name} failed in ensemble: {e}")
        
        if not results:
            raise OCREngineError("All engines failed in ensemble recognition")
        
        # 앙상블 전략 적용
        return self._apply_ensemble_strategy(results, strategy, valid_engines)
    
    def _apply_ensemble_strategy(self, results: List[OCRResult], 
                               strategy: str, engines: List[str]) -> OCRResult:
        """앙상블 전략 적용"""
        if strategy == "best_confidence":
            # 가장 높은 신뢰도를 가진 결과 선택
            best_result = max(results, key=lambda r: r.confidence)
            best_result.engine_used = f"Ensemble({','.join(engines)})"
            return best_result
        
        elif strategy == "weighted_average":
            # 신뢰도 가중 평균
            if not results:
                raise OCREngineError("No results for weighted average")
            
            # 동일한 텍스트를 반환하는 경우 가중 평균 신뢰도 계산
            texts = [r.text for r in results]
            if len(set(texts)) == 1:  # 모든 결과가 같은 텍스트
                avg_confidence = sum(r.confidence for r in results) / len(results)
                base_result = results[0]
                base_result.confidence = avg_confidence
                base_result.engine_used = f"Ensemble({','.join(engines)})"
                return base_result
            else:
                # 다른 텍스트인 경우 최고 신뢰도 선택
                return self._apply_ensemble_strategy(results, "best_confidence", engines)
        
        elif strategy == "voting":
            # 다수결 투표 (향후 구현)
            # 현재는 best_confidence로 대체
            return self._apply_ensemble_strategy(results, "best_confidence", engines)
        
        else:
            raise OCREngineError(f"Unknown ensemble strategy: {strategy}")
    
    def get_confidence_scores(self) -> Dict[str, float]:
        """각 엔진의 최근 신뢰도 점수 반환"""
        scores = {}
        for engine_name, confidences in self._confidence_history.items():
            if confidences:
                scores[engine_name] = confidences[-1]  # 최근 값
        return scores
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """각 엔진의 성능 통계 반환"""
        stats = {}
        for engine_name in self.available_engines:
            if engine_name in self._performance_history:
                times = self._performance_history[engine_name]
                confidences = self._confidence_history.get(engine_name, [])
                
                stats[engine_name] = {
                    "avg_time": sum(times) / len(times) if times else 0.0,
                    "min_time": min(times) if times else 0.0,
                    "max_time": max(times) if times else 0.0,
                    "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
                    "recognition_count": len(times)
                }
        return stats
    
    def _update_statistics(self, engine_name: str, result: OCRResult) -> None:
        """통계 정보 업데이트"""
        if engine_name not in self._confidence_history:
            self._confidence_history[engine_name] = []
        if engine_name not in self._performance_history:
            self._performance_history[engine_name] = []
        
        self._confidence_history[engine_name].append(result.confidence)
        self._performance_history[engine_name].append(result.processing_time)
        
        # 히스토리 크기 제한 (최근 100개)
        if len(self._confidence_history[engine_name]) > 100:
            self._confidence_history[engine_name] = self._confidence_history[engine_name][-100:]
        if len(self._performance_history[engine_name]) > 100:
            self._performance_history[engine_name] = self._performance_history[engine_name][-100:]
    
    def clear_statistics(self) -> None:
        """통계 정보 초기화"""
        self._confidence_history.clear()
        self._performance_history.clear()
    
    def get_engine_info(self) -> Dict[str, Any]:
        """엔진 정보 반환"""
        info = {
            "available_engines": self.available_engines,
            "current_engine": self.current_engine,
            "default_engine": self.default_engine,
            "engine_details": {}
        }
        
        for engine_name, engine in self.engines.items():
            info["engine_details"][engine_name] = {
                "name": engine.engine_name,
                "initialized": engine._is_initialized,
                "error": str(engine._initialization_error) if engine._initialization_error else None
            }
        
        return info