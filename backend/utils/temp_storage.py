"""
TempStorage - 임시 파일 저장소 관리 클래스
사용자별 파일 접근 권한, TTL 기반 자동 정리, 메타데이터 관리 기능을 제공합니다.
"""

import os
import json
import uuid
import time
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import shutil


class StorageError(Exception):
    """저장소 관련 오류"""
    pass


@dataclass
class FileInfo:
    """파일 정보 데이터 클래스"""
    content: bytes
    filename: str
    uploader_id: str
    created_at: datetime
    file_size: int


@dataclass
class StorageUsage:
    """저장소 사용량 정보"""
    total_files: int
    total_size: int
    files_by_user: Dict[str, int]


class TempStorage:
    """임시 파일 저장소 관리 클래스"""
    
    def __init__(self, base_path: str = "./temp_storage", ttl_seconds: int = 86400):
        """
        TempStorage 초기화
        
        Args:
            base_path: 기본 저장 경로
            ttl_seconds: 파일 TTL (기본 24시간)
        """
        self.base_path = Path(base_path)
        self.ttl_seconds = ttl_seconds
        self.metadata_file = self.base_path / "metadata.json"
        self._lock = threading.RLock()
        
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageError(f"Cannot create storage directory: {e}")
        
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """메타데이터 파일에서 파일 정보를 로드"""
        with self._lock:
            if self.metadata_file.exists():
                try:
                    with open(self.metadata_file, 'r') as f:
                        self._metadata = json.load(f)
                except Exception:
                    self._metadata = {}
            else:
                self._metadata = {}
    
    def _save_metadata(self) -> None:
        """메타데이터를 파일에 저장"""
        with self._lock:
            try:
                with open(self.metadata_file, 'w') as f:
                    json.dump(self._metadata, f, indent=2)
            except Exception as e:
                raise StorageError(f"Cannot save metadata: {e}")
    
    def generate_file_id(self) -> str:
        """고유한 파일 ID 생성"""
        return str(uuid.uuid4())
    
    def _get_file_path(self, file_id: str) -> Path:
        """파일 ID로부터 실제 파일 경로 생성"""
        return self.base_path / f"{file_id}.bin"
    
    def save_file(self, content: bytes, filename: str, uploader_id: str) -> str:
        """
        파일을 저장하고 고유 ID를 반환
        
        Args:
            content: 파일 내용
            filename: 원본 파일명
            uploader_id: 업로더 ID
            
        Returns:
            파일 고유 ID
        """
        file_id = self.generate_file_id()
        file_path = self._get_file_path(file_id)
        
        try:
            # 파일 저장
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # 메타데이터 저장
            with self._lock:
                self._metadata[file_id] = {
                    'filename': filename,
                    'uploader_id': uploader_id,
                    'created_at': datetime.now().isoformat(),
                    'file_size': len(content),
                    'file_path': str(file_path)
                }
                self._save_metadata()
            
            return file_id
            
        except Exception as e:
            # 저장 실패 시 정리
            if file_path.exists():
                file_path.unlink()
            raise StorageError(f"Cannot save file: {e}")
    
    def file_exists(self, file_id: str) -> bool:
        """
        파일 존재 여부 확인

        Args:
            file_id: 파일 고유 ID

        Returns:
            파일 존재 여부
        """
        with self._lock:
            metadata = self._metadata.get(file_id)
            if not metadata:
                return False

            file_path = self._get_file_path(file_id)
            return file_path.exists()

    def get_file(self, file_id: str, user_id: str) -> Optional[FileInfo]:
        """
        파일 ID와 사용자 ID로 파일 정보를 반환

        Args:
            file_id: 파일 고유 ID
            user_id: 요청 사용자 ID

        Returns:
            파일 정보 또는 None
        """
        with self._lock:
            metadata = self._metadata.get(file_id)
            if not metadata:
                return None

            # 접근 권한 확인
            if metadata['uploader_id'] != user_id:
                return None

            file_path = self._get_file_path(file_id)
            if not file_path.exists():
                # 파일이 없으면 메타데이터도 정리
                del self._metadata[file_id]
                self._save_metadata()
                return None

            try:
                with open(file_path, 'rb') as f:
                    content = f.read()

                return FileInfo(
                    content=content,
                    filename=metadata['filename'],
                    uploader_id=metadata['uploader_id'],
                    created_at=datetime.fromisoformat(metadata['created_at']),
                    file_size=metadata['file_size']
                )
            except Exception:
                return None
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        파일을 삭제
        
        Args:
            file_id: 파일 고유 ID
            user_id: 요청 사용자 ID
            
        Returns:
            삭제 성공 여부
        """
        with self._lock:
            metadata = self._metadata.get(file_id)
            if not metadata:
                return False
            
            # 접근 권한 확인
            if metadata['uploader_id'] != user_id:
                return False
            
            try:
                # 파일 삭제
                file_path = self._get_file_path(file_id)
                if file_path.exists():
                    file_path.unlink()
                
                # 메타데이터 삭제
                del self._metadata[file_id]
                self._save_metadata()
                
                return True
            except Exception:
                return False
    
    def cleanup_expired_files(self, current_time: Optional[float] = None) -> int:
        """
        만료된 파일들을 정리
        
        Args:
            current_time: 현재 시간 (테스트용, None이면 실제 시간 사용)
        
        Returns:
            정리된 파일 수
        """
        if current_time is None:
            current_time = time.time()
        
        cleaned_count = 0
        
        with self._lock:
            expired_ids = []
            
            for file_id, metadata in self._metadata.items():
                created_at = datetime.fromisoformat(metadata['created_at'])
                created_timestamp = created_at.timestamp()
                
                if current_time - created_timestamp > self.ttl_seconds:
                    expired_ids.append(file_id)
            
            for file_id in expired_ids:
                try:
                    file_path = self._get_file_path(file_id)
                    if file_path.exists():
                        file_path.unlink()
                    
                    del self._metadata[file_id]
                    cleaned_count += 1
                except Exception:
                    continue
            
            if cleaned_count > 0:
                self._save_metadata()
        
        return cleaned_count
    
    def get_storage_usage(self) -> StorageUsage:
        """
        저장소 사용량 정보를 반환
        
        Returns:
            저장소 사용량 정보
        """
        with self._lock:
            total_files = len(self._metadata)
            total_size = sum(meta['file_size'] for meta in self._metadata.values())
            
            files_by_user = {}
            for metadata in self._metadata.values():
                user_id = metadata['uploader_id']
                files_by_user[user_id] = files_by_user.get(user_id, 0) + 1
            
            return StorageUsage(
                total_files=total_files,
                total_size=total_size,
                files_by_user=files_by_user
            )