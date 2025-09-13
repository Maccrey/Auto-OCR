"""
TempStorage 클래스 테스트
TDD 방식으로 임시 파일 저장소 기능을 테스트합니다.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import time
import os
from datetime import datetime, timedelta

from backend.utils.temp_storage import TempStorage, StorageError


class TestTempStorage:
    """TempStorage 클래스 테스트 케이스"""
    
    @pytest.fixture
    def temp_dir(self):
        """테스트용 임시 디렉토리 생성"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def storage(self, temp_dir):
        """TempStorage 인스턴스 생성"""
        return TempStorage(base_path=temp_dir, ttl_seconds=3600)
    
    @pytest.fixture
    def sample_file_content(self):
        """샘플 파일 내용"""
        return b"This is a test PDF content"
    
    def test_init_creates_base_directory(self, temp_dir):
        """TempStorage 초기화 시 기본 디렉토리가 생성되는지 테스트"""
        base_path = Path(temp_dir) / "custom_storage"
        storage = TempStorage(base_path=str(base_path))
        
        assert base_path.exists()
        assert base_path.is_dir()
    
    def test_save_file_returns_unique_id(self, storage, sample_file_content):
        """파일 저장 시 고유한 ID가 반환되는지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        
        assert isinstance(file_id, str)
        assert len(file_id) > 0
        assert file_id != storage.save_file(sample_file_content, "test2.pdf", "user123")
    
    def test_save_file_creates_file_on_disk(self, storage, sample_file_content):
        """파일 저장 시 실제로 디스크에 파일이 생성되는지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        
        # 파일이 실제로 생성되었는지 확인
        file_path = storage._get_file_path(file_id)
        assert file_path.exists()
        
        # 파일 내용이 올바른지 확인
        with open(file_path, 'rb') as f:
            assert f.read() == sample_file_content
    
    def test_get_file_returns_correct_content(self, storage, sample_file_content):
        """파일 ID로 올바른 파일 내용을 반환하는지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        
        retrieved_info = storage.get_file(file_id, "user123")
        
        assert retrieved_info is not None
        assert retrieved_info.content == sample_file_content
        assert retrieved_info.filename == "test.pdf"
        assert retrieved_info.uploader_id == "user123"
    
    def test_get_file_with_wrong_user_returns_none(self, storage, sample_file_content):
        """잘못된 사용자 ID로 파일 접근 시 None을 반환하는지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        
        result = storage.get_file(file_id, "wrong_user")
        
        assert result is None
    
    def test_get_file_with_invalid_id_returns_none(self, storage):
        """존재하지 않는 파일 ID로 접근 시 None을 반환하는지 테스트"""
        result = storage.get_file("invalid_id", "user123")
        
        assert result is None
    
    def test_delete_file_removes_file_and_metadata(self, storage, sample_file_content):
        """파일 삭제 시 파일과 메타데이터가 모두 제거되는지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        file_path = storage._get_file_path(file_id)
        
        # 파일이 존재하는지 확인
        assert file_path.exists()
        
        # 파일 삭제
        success = storage.delete_file(file_id, "user123")
        
        assert success is True
        assert not file_path.exists()
        assert storage.get_file(file_id, "user123") is None
    
    def test_delete_file_with_wrong_user_fails(self, storage, sample_file_content):
        """잘못된 사용자 ID로 파일 삭제 시 실패하는지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        
        success = storage.delete_file(file_id, "wrong_user")
        
        assert success is False
        # 파일이 여전히 존재하는지 확인
        assert storage.get_file(file_id, "user123") is not None
    
    def test_cleanup_expired_files_removes_old_files(self, storage, sample_file_content):
        """만료된 파일들이 정리되는지 테스트"""
        # 파일 저장
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        
        # 현재 시간을 가져와서 TTL 이후의 시간을 시뮬레이션
        current_time = time.time() + 3700  # TTL(3600)보다 100초 더 미래
        
        # 정리 실행 (미래 시간을 직접 전달)
        cleaned_count = storage.cleanup_expired_files(current_time=current_time)
        
        assert cleaned_count >= 1
        assert storage.get_file(file_id, "user123") is None
    
    def test_generate_file_id_returns_unique_ids(self, storage):
        """파일 ID 생성 시 고유한 ID를 반환하는지 테스트"""
        id1 = storage.generate_file_id()
        id2 = storage.generate_file_id()
        
        assert id1 != id2
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert len(id1) > 0
        assert len(id2) > 0
    
    def test_get_storage_usage_returns_correct_info(self, storage, sample_file_content):
        """저장소 사용량 정보가 올바르게 반환되는지 테스트"""
        # 파일들 저장
        file1_id = storage.save_file(sample_file_content, "test1.pdf", "user123")
        file2_id = storage.save_file(sample_file_content * 2, "test2.pdf", "user456")
        
        usage = storage.get_storage_usage()
        
        assert usage.total_files >= 2
        assert usage.total_size > 0
        assert len(usage.files_by_user) >= 2
    
    def test_file_info_dataclass_structure(self, storage, sample_file_content):
        """FileInfo 데이터 클래스 구조가 올바른지 테스트"""
        file_id = storage.save_file(sample_file_content, "test.pdf", "user123")
        file_info = storage.get_file(file_id, "user123")
        
        assert hasattr(file_info, 'content')
        assert hasattr(file_info, 'filename')
        assert hasattr(file_info, 'uploader_id')
        assert hasattr(file_info, 'created_at')
        assert hasattr(file_info, 'file_size')
        
        assert isinstance(file_info.created_at, datetime)
        assert file_info.file_size == len(sample_file_content)
    
    def test_save_file_with_large_content_succeeds(self, storage):
        """대용량 파일 저장이 성공하는지 테스트"""
        large_content = b"x" * (1024 * 1024)  # 1MB
        
        file_id = storage.save_file(large_content, "large.pdf", "user123")
        retrieved_info = storage.get_file(file_id, "user123")
        
        assert retrieved_info is not None
        assert len(retrieved_info.content) == len(large_content)
    
    def test_concurrent_save_operations_succeed(self, storage, sample_file_content):
        """동시 파일 저장 작업이 성공하는지 테스트"""
        import threading
        
        results = []
        errors = []
        
        def save_file_worker(user_id):
            try:
                file_id = storage.save_file(
                    sample_file_content, 
                    f"test_{user_id}.pdf", 
                    f"user_{user_id}"
                )
                results.append(file_id)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=save_file_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        assert len(set(results)) == 10  # 모든 ID가 고유한지 확인
    
    def test_storage_error_raised_on_invalid_path(self):
        """잘못된 경로로 초기화 시 StorageError가 발생하는지 테스트"""
        with pytest.raises(StorageError):
            TempStorage(base_path="/invalid/path/that/cannot/be/created")
    
    def test_metadata_persistence_across_restarts(self, temp_dir, sample_file_content):
        """재시작 후에도 메타데이터가 유지되는지 테스트"""
        # 첫 번째 스토리지 인스턴스로 파일 저장
        storage1 = TempStorage(base_path=temp_dir)
        file_id = storage1.save_file(sample_file_content, "test.pdf", "user123")
        
        # 새로운 스토리지 인스턴스로 파일 접근
        storage2 = TempStorage(base_path=temp_dir)
        retrieved_info = storage2.get_file(file_id, "user123")
        
        assert retrieved_info is not None
        assert retrieved_info.filename == "test.pdf"
        assert retrieved_info.uploader_id == "user123"