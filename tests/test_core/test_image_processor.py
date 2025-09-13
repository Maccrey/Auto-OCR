"""
ImageProcessor 클래스 테스트
TDD 방식으로 이미지 전처리 기능을 테스트합니다.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import shutil
from pathlib import Path
from typing import Optional

from backend.core.image_processor import ImageProcessor, ProcessingError, ProcessingOptions


class TestImageProcessor:
    """ImageProcessor 클래스 테스트 케이스"""
    
    @pytest.fixture
    def temp_dir(self):
        """테스트용 임시 디렉토리 생성"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def processor(self, temp_dir):
        """ImageProcessor 인스턴스 생성"""
        return ImageProcessor(output_dir=temp_dir)
    
    @pytest.fixture
    def sample_image_array(self):
        """샘플 이미지 배열 (RGB)"""
        # 100x100 컬러 이미지 생성
        return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    
    @pytest.fixture
    def sample_gray_image_array(self):
        """샘플 그레이스케일 이미지 배열"""
        # 100x100 그레이스케일 이미지 생성
        return np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    
    @pytest.fixture
    def sample_image_path(self, temp_dir):
        """샘플 이미지 파일 경로"""
        image_path = Path(temp_dir) / "sample.png"
        # 빈 이미지 파일 생성 (실제 테스트에서는 mock을 사용)
        image_path.write_bytes(b"fake_image_data")
        return str(image_path)
    
    def test_init_creates_output_directory(self, temp_dir):
        """ImageProcessor 초기화 시 출력 디렉토리가 생성되는지 테스트"""
        output_dir = Path(temp_dir) / "processed"
        processor = ImageProcessor(output_dir=str(output_dir))
        
        assert output_dir.exists()
        assert output_dir.is_dir()
        assert processor.output_dir == output_dir
    
    @patch('cv2.imread')
    def test_load_image_returns_array(self, mock_imread, processor, sample_image_path, sample_image_array):
        """이미지 로드 시 numpy 배열을 반환하는지 테스트"""
        mock_imread.return_value = sample_image_array
        
        image = processor.load_image(sample_image_path)
        
        assert image is not None
        assert isinstance(image, np.ndarray)
        assert image.shape == sample_image_array.shape
        mock_imread.assert_called_once_with(sample_image_path)
    
    @patch('cv2.imread')
    def test_load_image_with_invalid_path(self, mock_imread, processor):
        """잘못된 경로의 이미지 로드 테스트"""
        mock_imread.return_value = None
        
        image = processor.load_image("invalid_path.jpg")
        
        assert image is None
    
    def test_load_image_with_nonexistent_file(self, processor):
        """존재하지 않는 파일 로드 테스트"""
        image = processor.load_image("nonexistent.jpg")
        
        assert image is None
    
    @patch('cv2.cvtColor')
    def test_convert_to_grayscale_with_color_image(self, mock_cvtColor, processor, sample_image_array, sample_gray_image_array):
        """컬러 이미지를 그레이스케일로 변환 테스트"""
        mock_cvtColor.return_value = sample_gray_image_array
        
        gray_image = processor.convert_to_grayscale(sample_image_array)
        
        assert gray_image is not None
        assert isinstance(gray_image, np.ndarray)
        assert len(gray_image.shape) == 2  # 그레이스케일은 2차원
        mock_cvtColor.assert_called_once()
    
    def test_convert_to_grayscale_with_gray_image(self, processor, sample_gray_image_array):
        """이미 그레이스케일인 이미지 변환 테스트"""
        gray_image = processor.convert_to_grayscale(sample_gray_image_array)
        
        # 이미 그레이스케일이면 그대로 반환
        assert np.array_equal(gray_image, sample_gray_image_array)
    
    @patch('cv2.createCLAHE')
    def test_apply_clahe_enhances_contrast(self, mock_createCLAHE, processor, sample_gray_image_array):
        """CLAHE 대비 향상 테스트"""
        mock_clahe = MagicMock()
        mock_clahe.apply.return_value = sample_gray_image_array
        mock_createCLAHE.return_value = mock_clahe
        
        enhanced_image = processor.apply_clahe(sample_gray_image_array, clip_limit=2.0, grid_size=(8, 8))
        
        assert enhanced_image is not None
        assert isinstance(enhanced_image, np.ndarray)
        mock_createCLAHE.assert_called_once_with(clipLimit=2.0, tileGridSize=(8, 8))
        mock_clahe.apply.assert_called_once_with(sample_gray_image_array)
    
    @patch('cv2.minAreaRect')
    @patch('cv2.findContours')
    @patch('cv2.threshold')
    def test_deskew_image_corrects_rotation(self, mock_threshold, mock_findContours, mock_minAreaRect, processor, sample_gray_image_array):
        """기울기 보정 테스트"""
        # Mock 설정
        mock_threshold.return_value = (None, sample_gray_image_array)
        mock_contour = np.array([[[0, 0]], [[50, 0]], [[50, 50]], [[0, 50]]])
        mock_findContours.return_value = ([mock_contour], None)
        mock_minAreaRect.return_value = ((25, 25), (50, 50), 15.0)  # 15도 회전
        
        with patch('cv2.getRotationMatrix2D') as mock_getRotationMatrix2D, \
             patch('cv2.warpAffine') as mock_warpAffine:
            
            mock_getRotationMatrix2D.return_value = np.eye(2, 3)
            mock_warpAffine.return_value = sample_gray_image_array
            
            deskewed_image = processor.deskew_image(sample_gray_image_array)
            
            assert deskewed_image is not None
            assert isinstance(deskewed_image, np.ndarray)
            mock_getRotationMatrix2D.assert_called_once()
            mock_warpAffine.assert_called_once()
    
    @patch('cv2.morphologyEx')
    @patch('cv2.getStructuringElement')
    def test_remove_noise_cleans_image(self, mock_getStructuringElement, mock_morphologyEx, processor, sample_gray_image_array):
        """노이즈 제거 테스트"""
        mock_kernel = np.ones((3, 3), np.uint8)
        mock_getStructuringElement.return_value = mock_kernel
        mock_morphologyEx.return_value = sample_gray_image_array
        
        cleaned_image = processor.remove_noise(sample_gray_image_array, kernel_size=3)
        
        assert cleaned_image is not None
        assert isinstance(cleaned_image, np.ndarray)
        mock_getStructuringElement.assert_called()
        mock_morphologyEx.assert_called()
    
    @patch('cv2.adaptiveThreshold')
    def test_apply_adaptive_threshold_binarizes_image(self, mock_adaptiveThreshold, processor, sample_gray_image_array):
        """적응형 임계값 이진화 테스트"""
        binary_image = np.random.randint(0, 255, sample_gray_image_array.shape, dtype=np.uint8)
        mock_adaptiveThreshold.return_value = binary_image
        
        result = processor.apply_adaptive_threshold(sample_gray_image_array)
        
        assert result is not None
        assert isinstance(result, np.ndarray)
        mock_adaptiveThreshold.assert_called_once()
    
    def test_processing_options_default_values(self):
        """ProcessingOptions 기본값 테스트"""
        options = ProcessingOptions()
        
        assert options.apply_clahe is True
        assert options.deskew_enabled is True
        assert options.noise_removal is True
        assert options.adaptive_threshold is True
        assert options.super_resolution is False
        assert options.clahe_clip_limit == 2.0
        assert options.clahe_grid_size == (8, 8)
        assert options.noise_kernel_size == 3
    
    def test_processing_options_custom_values(self):
        """ProcessingOptions 커스텀 값 테스트"""
        options = ProcessingOptions(
            apply_clahe=False,
            deskew_enabled=False,
            clahe_clip_limit=3.0,
            clahe_grid_size=(16, 16),
            noise_kernel_size=5
        )
        
        assert options.apply_clahe is False
        assert options.deskew_enabled is False
        assert options.clahe_clip_limit == 3.0
        assert options.clahe_grid_size == (16, 16)
        assert options.noise_kernel_size == 5
    
    @patch('cv2.imwrite')
    def test_save_image_writes_to_file(self, mock_imwrite, processor, sample_gray_image_array):
        """이미지 저장 테스트"""
        mock_imwrite.return_value = True
        
        output_path = processor.save_image(sample_gray_image_array, "test.png")
        
        assert output_path is not None
        assert output_path.endswith("test.png")
        mock_imwrite.assert_called_once()
    
    @patch('cv2.imwrite')
    def test_save_image_fails_gracefully(self, mock_imwrite, processor, sample_gray_image_array):
        """이미지 저장 실패 테스트"""
        mock_imwrite.return_value = False
        
        with pytest.raises(ProcessingError):
            processor.save_image(sample_gray_image_array, "test.png")
    
    def test_preprocess_pipeline_with_all_options(self, processor, sample_image_path):
        """전체 전처리 파이프라인 테스트 (모든 옵션 활성화)"""
        options = ProcessingOptions(
            apply_clahe=True,
            deskew_enabled=True,
            noise_removal=True,
            adaptive_threshold=True
        )
        
        with patch.object(processor, 'load_image') as mock_load, \
             patch.object(processor, 'convert_to_grayscale') as mock_gray, \
             patch.object(processor, 'apply_clahe') as mock_clahe, \
             patch.object(processor, 'deskew_image') as mock_deskew, \
             patch.object(processor, 'remove_noise') as mock_noise, \
             patch.object(processor, 'apply_adaptive_threshold') as mock_threshold, \
             patch.object(processor, 'save_image') as mock_save:
            
            # Mock 설정
            mock_load.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_gray.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_clahe.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_deskew.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_noise.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_threshold.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_save.return_value = "output.png"
            
            result_path = processor.preprocess_pipeline(sample_image_path, options)
            
            assert result_path == "output.png"
            mock_load.assert_called_once()
            mock_gray.assert_called_once()
            mock_clahe.assert_called_once()
            mock_deskew.assert_called_once()
            mock_noise.assert_called_once()
            mock_threshold.assert_called_once()
            mock_save.assert_called_once()
    
    def test_preprocess_pipeline_with_minimal_options(self, processor, sample_image_path):
        """전처리 파이프라인 테스트 (최소 옵션)"""
        options = ProcessingOptions(
            apply_clahe=False,
            deskew_enabled=False,
            noise_removal=False,
            adaptive_threshold=False
        )
        
        with patch.object(processor, 'load_image') as mock_load, \
             patch.object(processor, 'convert_to_grayscale') as mock_gray, \
             patch.object(processor, 'save_image') as mock_save:
            
            # Mock 설정
            mock_load.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_gray.return_value = np.zeros((100, 100), dtype=np.uint8)
            mock_save.return_value = "output.png"
            
            result_path = processor.preprocess_pipeline(sample_image_path, options)
            
            assert result_path == "output.png"
            mock_load.assert_called_once()
            mock_gray.assert_called_once()
            mock_save.assert_called_once()
    
    def test_preprocess_pipeline_with_invalid_image(self, processor):
        """잘못된 이미지로 전처리 파이프라인 테스트"""
        options = ProcessingOptions()
        
        with patch.object(processor, 'load_image', return_value=None):
            with pytest.raises(ProcessingError):
                processor.preprocess_pipeline("invalid.jpg", options)
    
    def test_get_preprocessing_preview_returns_dict(self, processor, sample_image_path):
        """전처리 미리보기 딕셔너리 반환 테스트"""
        with patch.object(processor, 'load_image') as mock_load, \
             patch.object(processor, 'convert_to_grayscale') as mock_gray, \
             patch.object(processor, 'apply_clahe') as mock_clahe, \
             patch.object(processor, 'deskew_image') as mock_deskew, \
             patch.object(processor, 'remove_noise') as mock_noise, \
             patch.object(processor, 'apply_adaptive_threshold') as mock_threshold:
            
            # Mock 설정
            sample_array = np.zeros((100, 100, 3), dtype=np.uint8)
            gray_array = np.zeros((100, 100), dtype=np.uint8)
            
            mock_load.return_value = sample_array
            mock_gray.return_value = gray_array
            mock_clahe.return_value = gray_array
            mock_deskew.return_value = gray_array
            mock_noise.return_value = gray_array
            mock_threshold.return_value = gray_array
            
            preview = processor.get_preprocessing_preview(sample_image_path)
            
            assert isinstance(preview, dict)
            assert 'original' in preview
            assert 'grayscale' in preview
            assert 'clahe' in preview
            assert 'deskewed' in preview
            assert 'denoised' in preview
            assert 'threshold' in preview
    
    def test_processing_error_message(self):
        """ProcessingError 메시지 테스트"""
        error_msg = "Test processing error"
        error = ProcessingError(error_msg)
        
        assert str(error) == error_msg
        assert isinstance(error, Exception)
    
    def test_concurrent_processing_operations(self, processor):
        """동시 처리 작업 테스트"""
        import threading
        
        results = []
        errors = []
        
        def process_worker(worker_id):
            try:
                # 간단한 그레이스케일 변환 테스트
                test_image = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
                gray_image = processor.convert_to_grayscale(test_image)
                results.append(gray_image)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=process_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        for result in results:
            assert isinstance(result, np.ndarray)
            assert len(result.shape) == 2  # 그레이스케일