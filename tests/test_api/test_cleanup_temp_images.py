"""
임시 이미지 파일 정리 테스트
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock
from backend.api.processing import cleanup_temp_images


class TestCleanupTempImages:
    """임시 이미지 파일 정리 함수 테스트"""

    def test_cleanup_existing_files(self, tmp_path):
        """존재하는 파일들을 정상적으로 정리"""
        # 임시 파일 생성
        temp_images = []
        processed_images = []
        
        for i in range(3):
            temp_file = tmp_path / f"temp_{i}.png"
            temp_file.write_text("temp image")
            temp_images.append(str(temp_file))
            
            proc_file = tmp_path / f"processed_{i}.png"
            proc_file.write_text("processed image")
            processed_images.append(str(proc_file))
        
        # Mock logger
        logger = Mock()
        
        # 정리 실행
        cleanup_temp_images(temp_images, processed_images, logger)
        
        # 파일이 모두 삭제되었는지 확인
        for file_path in temp_images + processed_images:
            assert not os.path.exists(file_path)
        
        # 로그 확인
        assert logger.info.called
        assert "Cleaned up 6 temporary image files" in str(logger.info.call_args)

    def test_cleanup_nonexistent_files(self):
        """존재하지 않는 파일 처리"""
        # 존재하지 않는 파일 경로
        temp_images = ["/nonexistent/temp_1.png", "/nonexistent/temp_2.png"]
        processed_images = ["/nonexistent/proc_1.png"]
        
        logger = Mock()
        
        # 정리 실행 (예외 발생하지 않아야 함)
        cleanup_temp_images(temp_images, processed_images, logger)
        
        # 경고 로그가 없어야 함 (파일이 없으면 조용히 스킵)
        assert not logger.warning.called

    def test_cleanup_mixed_files(self, tmp_path):
        """존재하는 파일과 없는 파일 혼합"""
        # 일부만 생성
        existing_file = tmp_path / "existing.png"
        existing_file.write_text("image")
        
        temp_images = [str(existing_file), "/nonexistent/file.png"]
        processed_images = []
        
        logger = Mock()
        
        cleanup_temp_images(temp_images, processed_images, logger)
        
        # 존재했던 파일만 삭제됨
        assert not existing_file.exists()
        assert logger.info.called

    def test_cleanup_with_permission_error(self, tmp_path, monkeypatch):
        """권한 오류 발생 시 처리"""
        temp_file = tmp_path / "temp.png"
        temp_file.write_text("image")
        
        temp_images = [str(temp_file)]
        processed_images = []
        
        logger = Mock()
        
        # os.remove를 Mock하여 권한 오류 시뮬레이션
        def mock_remove(path):
            raise PermissionError("Permission denied")
        
        monkeypatch.setattr("os.remove", mock_remove)
        
        # 정리 실행 (예외 발생하지 않아야 함)
        cleanup_temp_images(temp_images, processed_images, logger)
        
        # 경고 로그 확인
        assert logger.warning.called
        assert "Failed to cleanup" in str(logger.warning.call_args)

    def test_cleanup_empty_lists(self):
        """빈 리스트 처리"""
        logger = Mock()
        
        cleanup_temp_images([], [], logger)
        
        # 로그가 호출되지 않아야 함
        assert not logger.info.called
        assert not logger.warning.called

    def test_cleanup_with_none_values(self):
        """None 값 포함 시 처리"""
        temp_images = [None, "some_path.png", None]
        processed_images = []
        
        logger = Mock()
        
        # 예외 발생하지 않아야 함
        cleanup_temp_images(temp_images, processed_images, logger)

    def test_cleanup_with_directories(self, tmp_path):
        """디렉토리는 건드리지 않음"""
        # 디렉토리 생성
        temp_dir = tmp_path / "temp_dir"
        temp_dir.mkdir()
        
        # 파일도 하나 생성
        temp_file = tmp_path / "temp.png"
        temp_file.write_text("image")
        
        temp_images = [str(temp_dir), str(temp_file)]
        processed_images = []
        
        logger = Mock()
        
        cleanup_temp_images(temp_images, processed_images, logger)
        
        # 디렉토리는 남아있어야 함
        assert temp_dir.exists()
        
        # 파일만 삭제됨
        assert not temp_file.exists()
        
        # 1개 파일만 정리됨
        assert "Cleaned up 1 temporary image files" in str(logger.info.call_args)
