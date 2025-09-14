#!/usr/bin/env python3
"""
K-OCR Web Corrector Health Check Script

Docker 컨테이너의 헬스체크를 위한 스크립트입니다.
각 서비스의 상태를 종합적으로 점검합니다.
"""

import os
import sys
import time
import json
import logging
import requests
from typing import Dict, Any, Optional
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.WARNING)  # Health check는 조용히 실행
logger = logging.getLogger(__name__)


class HealthChecker:
    """헬스체크 수행 클래스"""

    def __init__(self):
        self.timeout = int(os.getenv('HEALTH_CHECK_TIMEOUT', '10'))
        self.base_url = os.getenv('HEALTH_CHECK_URL', 'http://localhost:8000')

    def check_web_service(self) -> bool:
        """웹 서비스 헬스체크"""
        try:
            response = requests.get(
                f"{self.base_url}/api/download/health",
                timeout=self.timeout
            )
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"Web service health check failed: {e}")
            return False

    def check_redis_connection(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            import redis

            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            r.ping()
            return True

        except Exception as e:
            logger.debug(f"Redis health check failed: {e}")
            return False

    def check_celery_worker(self) -> bool:
        """Celery 워커 상태 확인"""
        try:
            from celery import Celery

            broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
            app = Celery('health_check', broker=broker_url)

            # 활성 워커 확인
            inspect = app.control.inspect()
            stats = inspect.stats()

            return bool(stats and len(stats) > 0)

        except Exception as e:
            logger.debug(f"Celery health check failed: {e}")
            return False

    def check_database_connection(self) -> bool:
        """데이터베이스 연결 확인 (선택사항)"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return True  # DB가 설정되지 않으면 성공으로 간주

            import psycopg2
            conn = psycopg2.connect(database_url)
            conn.close()
            return True

        except Exception as e:
            logger.debug(f"Database health check failed: {e}")
            return False

    def check_disk_space(self) -> bool:
        """디스크 공간 확인"""
        try:
            temp_path = Path(os.getenv('TEMP_STORAGE_PATH', '/app/temp_storage'))
            if not temp_path.exists():
                temp_path.mkdir(parents=True, exist_ok=True)

            stat = os.statvfs(str(temp_path))
            available_bytes = stat.f_frsize * stat.f_bavail
            available_gb = available_bytes / (1024 ** 3)

            # 최소 1GB 필요
            return available_gb > 1.0

        except Exception as e:
            logger.debug(f"Disk space check failed: {e}")
            return False

    def check_memory_usage(self) -> bool:
        """메모리 사용량 확인"""
        try:
            import psutil

            memory = psutil.virtual_memory()
            # 메모리 사용률이 90% 이하이면 정상
            return memory.percent < 90.0

        except ImportError:
            # psutil이 없으면 메모리 체크 스킵
            return True
        except Exception as e:
            logger.debug(f"Memory check failed: {e}")
            return False

    def check_ocr_models(self) -> bool:
        """OCR 모델 파일 존재 확인"""
        try:
            # PaddleOCR 모델 확인
            home = os.path.expanduser('~')
            paddle_dir = Path(home) / '.paddleocr'

            # 캐시된 모델 디렉토리도 확인
            cache_dir = Path('/app/models/paddleocr')

            return paddle_dir.exists() or cache_dir.exists()

        except Exception as e:
            logger.debug(f"OCR models check failed: {e}")
            return False

    def run_comprehensive_check(self) -> Dict[str, Any]:
        """종합 헬스체크 실행"""
        checks = {
            'web_service': self.check_web_service(),
            'redis': self.check_redis_connection(),
            'disk_space': self.check_disk_space(),
            'memory': self.check_memory_usage(),
            'ocr_models': self.check_ocr_models(),
        }

        # 환경에 따라 선택적 체크
        if os.getenv('ENVIRONMENT') == 'production':
            checks['celery_worker'] = self.check_celery_worker()
            checks['database'] = self.check_database_connection()

        # 전체 상태 계산
        all_passed = all(checks.values())
        critical_checks = ['web_service', 'disk_space']
        critical_passed = all(checks[check] for check in critical_checks if check in checks)

        return {
            'timestamp': time.time(),
            'overall_status': 'healthy' if all_passed else ('critical' if not critical_passed else 'degraded'),
            'checks': checks,
            'critical_passed': critical_passed
        }


def main():
    """메인 함수"""
    checker = HealthChecker()

    # 간단한 체크 또는 상세 체크 선택
    check_type = sys.argv[1] if len(sys.argv) > 1 else 'simple'

    if check_type == 'simple':
        # 기본 웹 서비스만 체크 (Docker 헬스체크용)
        if checker.check_web_service():
            sys.exit(0)
        else:
            sys.exit(1)

    elif check_type == 'comprehensive':
        # 종합 체크 실행
        result = checker.run_comprehensive_check()

        # JSON 형태로 결과 출력
        print(json.dumps(result, indent=2))

        # 크리티컬 체크가 통과하면 성공
        if result['critical_passed']:
            sys.exit(0)
        else:
            sys.exit(1)

    else:
        print(f"Usage: {sys.argv[0]} [simple|comprehensive]")
        sys.exit(1)


if __name__ == '__main__':
    main()