"""
ImageProcessor - 이미지 전처리 클래스
OpenCV를 사용하여 OCR 품질 향상을 위한 다양한 이미지 전처리 기능을 제공합니다.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import threading


class ProcessingError(Exception):
    """이미지 처리 관련 오류"""
    pass


@dataclass
class ProcessingOptions:
    """이미지 전처리 옵션 데이터 클래스"""
    apply_clahe: bool = True
    deskew_enabled: bool = True
    noise_removal: bool = True
    adaptive_threshold: bool = True
    super_resolution: bool = False
    clahe_clip_limit: float = 2.0
    clahe_grid_size: Tuple[int, int] = (8, 8)
    noise_kernel_size: int = 3


class ImageProcessor:
    """이미지 전처리를 담당하는 클래스"""
    
    def __init__(self, output_dir: str = "./processed_images"):
        """
        ImageProcessor 초기화
        
        Args:
            output_dir: 처리된 이미지 출력 디렉토리
        """
        self.output_dir = Path(output_dir)
        self._lock = threading.RLock()
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        이미지 파일을 로드
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            numpy 배열 또는 None
        """
        try:
            if not os.path.exists(image_path):
                return None
            
            image = cv2.imread(image_path)
            return image
        except Exception:
            return None
    
    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        이미지를 그레이스케일로 변환
        
        Args:
            image: 입력 이미지 (BGR 또는 그레이스케일)
            
        Returns:
            그레이스케일 이미지
        """
        if len(image.shape) == 2:
            # 이미 그레이스케일인 경우
            return image
        elif len(image.shape) == 3:
            # 컬러 이미지를 그레이스케일로 변환
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            raise ProcessingError(f"Unsupported image shape: {image.shape}")
    
    def apply_clahe(self, image: np.ndarray, clip_limit: float = 2.0, 
                   grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
        """
        CLAHE (Contrast Limited Adaptive Histogram Equalization) 적용
        
        Args:
            image: 그레이스케일 이미지
            clip_limit: 클립 제한값
            grid_size: 타일 그리드 크기
            
        Returns:
            대비가 향상된 이미지
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
        return clahe.apply(image)
    
    def deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        이미지 기울기 보정
        
        Args:
            image: 그레이스케일 이미지
            
        Returns:
            기울기가 보정된 이미지
        """
        try:
            # 이진화
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 윤곽선 찾기
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
            
            # 가장 큰 윤곽선 선택
            largest_contour = max(contours, key=cv2.contourArea)
            
            # 최소 사각형 찾기
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[2]
            
            # 각도 보정 (90도 이상인 경우 조정)
            if angle < -45:
                angle = 90 + angle
            
            # 회전 행렬 생성
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # 이미지 회전
            rotated = cv2.warpAffine(image, rotation_matrix, (w, h), 
                                   flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return rotated
        except Exception:
            # 오류 발생 시 원본 반환
            return image
    
    def remove_noise(self, image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
        """
        이미지 노이즈 제거
        
        Args:
            image: 그레이스케일 이미지
            kernel_size: 모폴로지 커널 크기
            
        Returns:
            노이즈가 제거된 이미지
        """
        # 모폴로지 연산을 위한 커널 생성
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        
        # Opening 연산 (침식 후 팽창) - 작은 노이즈 제거
        opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        
        # Closing 연산 (팽창 후 침식) - 작은 구멍 메우기
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        
        return closed
    
    def apply_adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        적응형 임계값을 사용한 이진화
        
        Args:
            image: 그레이스케일 이미지
            
        Returns:
            이진화된 이미지
        """
        return cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
    
    def save_image(self, image: np.ndarray, filename: str) -> str:
        """
        이미지를 파일로 저장
        
        Args:
            image: 저장할 이미지
            filename: 파일명
            
        Returns:
            저장된 파일의 전체 경로
            
        Raises:
            ProcessingError: 저장 실패 시
        """
        output_path = self.output_dir / filename
        
        success = cv2.imwrite(str(output_path), image)
        
        if not success:
            raise ProcessingError(f"Failed to save image: {output_path}")
        
        return str(output_path)
    
    def preprocess_pipeline(self, image_path: str, options: ProcessingOptions) -> str:
        """
        전체 전처리 파이프라인 실행
        
        Args:
            image_path: 입력 이미지 경로
            options: 전처리 옵션
            
        Returns:
            처리된 이미지 파일 경로
            
        Raises:
            ProcessingError: 처리 실패 시
        """
        try:
            with self._lock:
                # 1. 이미지 로드
                image = self.load_image(image_path)
                if image is None:
                    raise ProcessingError(f"Cannot load image: {image_path}")
                
                # 2. 그레이스케일 변환
                gray_image = self.convert_to_grayscale(image)
                
                # 3. CLAHE 적용 (옵션)
                if options.apply_clahe:
                    gray_image = self.apply_clahe(
                        gray_image, 
                        options.clahe_clip_limit, 
                        options.clahe_grid_size
                    )
                
                # 4. 기울기 보정 (옵션)
                if options.deskew_enabled:
                    gray_image = self.deskew_image(gray_image)
                
                # 5. 노이즈 제거 (옵션)
                if options.noise_removal:
                    gray_image = self.remove_noise(gray_image, options.noise_kernel_size)
                
                # 6. 적응형 임계값 (옵션)
                if options.adaptive_threshold:
                    gray_image = self.apply_adaptive_threshold(gray_image)
                
                # 7. 결과 저장
                input_filename = Path(image_path).stem
                output_filename = f"{input_filename}_processed.png"
                output_path = self.save_image(gray_image, output_filename)
                
                return output_path
        
        except Exception as e:
            if isinstance(e, ProcessingError):
                raise
            else:
                raise ProcessingError(f"Pipeline processing failed: {str(e)}")
    
    def get_preprocessing_preview(self, image_path: str) -> Dict[str, np.ndarray]:
        """
        전처리 단계별 미리보기 생성
        
        Args:
            image_path: 입력 이미지 경로
            
        Returns:
            단계별 처리 결과를 담은 딕셔너리
        """
        try:
            # 1. 원본 이미지 로드
            original = self.load_image(image_path)
            if original is None:
                raise ProcessingError(f"Cannot load image: {image_path}")
            
            # 2. 그레이스케일 변환
            grayscale = self.convert_to_grayscale(original)
            
            # 3. CLAHE 적용
            clahe = self.apply_clahe(grayscale)
            
            # 4. 기울기 보정
            deskewed = self.deskew_image(clahe)
            
            # 5. 노이즈 제거
            denoised = self.remove_noise(deskewed)
            
            # 6. 적응형 임계값
            threshold = self.apply_adaptive_threshold(denoised)
            
            return {
                'original': original,
                'grayscale': grayscale,
                'clahe': clahe,
                'deskewed': deskewed,
                'denoised': denoised,
                'threshold': threshold
            }
        
        except Exception as e:
            if isinstance(e, ProcessingError):
                raise
            else:
                raise ProcessingError(f"Preview generation failed: {str(e)}")