"""
공유 의존성 모듈
애플리케이션 전체에서 사용하는 싱글톤 인스턴스들을 관리합니다.
"""

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
        _temp_storage_instance = TempStorage()
    return _temp_storage_instance
