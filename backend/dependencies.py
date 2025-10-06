"""
공유 의존성 모듈
애플리케이션 전체에서 사용하는 싱글톤 인스턴스들을 관리합니다.
"""

import os
from pathlib import Path
from backend.utils.temp_storage import TempStorage

# 전역 임시 저장소 인스턴스 (싱글톤)
_temp_storage_instance = None


def get_temp_storage() -> TempStorage:
    """
    임시 저장소 싱글톤 인스턴스 반환

    Returns:
        TempStorage: 공유 임시 저장소 인스턴스
    """
    global _temp_storage_instance
    if _temp_storage_instance is None:
        # 절대 경로로 temp_storage 디렉토리 지정
        base_dir = Path(__file__).parent.parent  # /app 디렉토리
        temp_storage_path = base_dir / "temp_storage"
        _temp_storage_instance = TempStorage(base_path=str(temp_storage_path))
    return _temp_storage_instance
