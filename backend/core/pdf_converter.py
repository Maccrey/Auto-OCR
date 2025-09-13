"""
PDFConverter - PDF를 PNG 이미지로 변환하는 클래스
PyMuPDF(fitz)를 사용하여 고품질 이미지 변환을 제공합니다.
"""

import os
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import threading


class ConversionError(Exception):
    """PDF 변환 관련 오류"""
    pass


@dataclass
class PDFInfo:
    """PDF 파일 정보 데이터 클래스"""
    page_count: int
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    file_size: int


class PDFConverter:
    """PDF를 PNG 이미지로 변환하는 클래스"""
    
    def __init__(self, output_dir: str = "./temp_images", dpi: int = 200):
        """
        PDFConverter 초기화
        
        Args:
            output_dir: 이미지 출력 디렉토리
            dpi: 이미지 해상도 (DPI)
        """
        self.output_dir = Path(output_dir)
        self.dpi = dpi
        self._lock = threading.RLock()
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        PDF 파일이 유효한지 검증
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            유효성 여부
        """
        try:
            if not os.path.exists(pdf_path):
                return False
            
            with fitz.open(pdf_path) as doc:
                # 페이지 수를 확인하여 유효한 PDF인지 검증
                return doc.page_count > 0
        except Exception:
            return False
    
    def get_pdf_info(self, pdf_path: str) -> Optional[PDFInfo]:
        """
        PDF 파일 정보를 반환
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            PDF 정보 또는 None
        """
        try:
            if not os.path.exists(pdf_path):
                return None
            
            file_size = os.path.getsize(pdf_path)
            
            with fitz.open(pdf_path) as doc:
                metadata = doc.metadata
                
                return PDFInfo(
                    page_count=doc.page_count,
                    title=metadata.get('title', ''),
                    author=metadata.get('author', ''),
                    subject=metadata.get('subject', ''),
                    file_size=file_size
                )
        except Exception:
            return None
    
    def _get_output_filename(self, pdf_path: str, page_index: int, total_pages: int) -> str:
        """
        출력 파일명 생성
        
        Args:
            pdf_path: 원본 PDF 경로
            page_index: 페이지 인덱스 (0부터 시작)
            total_pages: 총 페이지 수
            
        Returns:
            출력 파일명
        """
        base_name = Path(pdf_path).stem
        
        if total_pages == 1:
            return f"{base_name}.png"
        else:
            return f"{base_name}_page_{page_index + 1}.png"
    
    def convert_pdf_to_png(self, pdf_path: str) -> List[str]:
        """
        PDF를 PNG 이미지들로 변환
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            생성된 PNG 파일 경로 리스트
            
        Raises:
            ConversionError: 변환 실패 시
        """
        try:
            if not os.path.exists(pdf_path):
                raise ConversionError(f"PDF file not found: {pdf_path}")
            
            image_paths = []
            
            with self._lock:
                with fitz.open(pdf_path) as doc:
                    total_pages = doc.page_count
                    
                    if total_pages == 0:
                        raise ConversionError("PDF has no pages")
                    
                    # DPI에 따른 스케일링 계산
                    zoom_factor = self.dpi / 72.0  # 72 DPI가 기본값
                    matrix = fitz.Matrix(zoom_factor, zoom_factor)
                    
                    for page_index in range(total_pages):
                        page = doc[page_index]
                        
                        # 페이지를 픽스맵(이미지)으로 렌더링
                        pixmap = page.get_pixmap(matrix=matrix)
                        
                        # 출력 파일명 생성
                        filename = self._get_output_filename(pdf_path, page_index, total_pages)
                        output_path = self.output_dir / filename
                        
                        # PNG 데이터 생성 및 저장
                        png_data = pixmap.pil_tobytes(format="PNG")
                        
                        with open(output_path, 'wb') as f:
                            f.write(png_data)
                        
                        image_paths.append(str(output_path))
                        
                        # 메모리 정리
                        pixmap = None
            
            return image_paths
            
        except Exception as e:
            if isinstance(e, ConversionError):
                raise
            else:
                raise ConversionError(f"Failed to convert PDF to PNG: {str(e)}")
    
    def estimate_processing_time(self, pdf_path: str) -> float:
        """
        PDF 처리 예상 시간 계산
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            예상 처리 시간 (초)
        """
        try:
            if not os.path.exists(pdf_path):
                return 0.0
            
            with fitz.open(pdf_path) as doc:
                page_count = doc.page_count
                
                # 페이지당 대략적인 처리 시간 (DPI에 따라 조정)
                base_time_per_page = 1.0  # 기본 1초
                dpi_factor = self.dpi / 200.0  # 200 DPI 기준
                time_per_page = base_time_per_page * dpi_factor
                
                return page_count * time_per_page
                
        except Exception:
            return 0.0