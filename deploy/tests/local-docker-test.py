#!/usr/bin/env python3
"""
K-OCR Web Corrector - 로컬 Docker 환경 테스트
로컬 개발 환경에서 Docker Compose를 사용한 전체 스택 테스트
"""

import os
import sys
import time
import json
import subprocess
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import docker
import yaml

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LocalDockerTester:
    """로컬 Docker 환경 테스트 클래스"""

    def __init__(self, project_root: str = None):
        """
        테스터 초기화

        Args:
            project_root: 프로젝트 루트 디렉토리 경로
        """
        self.project_root = Path(project_root or os.getcwd())
        self.docker_client = docker.from_env()
        self.compose_file = self.project_root / "docker-compose.yml"
        self.compose_dev_file = self.project_root / "docker-compose.dev.yml"
        self.base_url = "http://localhost:8000"
        self.test_results: List[Dict] = []

    def run_all_tests(self) -> bool:
        """모든 테스트 실행"""
        logger.info("=== K-OCR 로컬 Docker 환경 테스트 시작 ===")

        try:
            # 1. 환경 검증
            if not self._validate_environment():
                return False

            # 2. Docker Compose 빌드 및 시작
            if not self._setup_docker_environment():
                return False

            # 3. 서비스 헬스 체크
            if not self._wait_for_services():
                return False

            # 4. 기능 테스트
            if not self._run_functional_tests():
                return False

            # 5. 성능 테스트
            if not self._run_performance_tests():
                return False

            # 6. 리소스 사용량 체크
            if not self._check_resource_usage():
                return False

            # 7. 로그 검증
            if not self._validate_logs():
                return False

            logger.info("=== 모든 테스트 통과 ===")
            self._print_test_summary()
            return True

        except Exception as e:
            logger.error(f"테스트 실행 중 오류 발생: {e}")
            return False
        finally:
            self._cleanup()

    def _validate_environment(self) -> bool:
        """환경 검증"""
        logger.info("환경 검증 중...")

        # Docker 및 Docker Compose 확인
        try:
            result = subprocess.run(['docker', '--version'],
                                  capture_output=True, text=True)
            logger.info(f"Docker 버전: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Docker가 설치되지 않았습니다.")
            return False

        try:
            result = subprocess.run(['docker-compose', '--version'],
                                  capture_output=True, text=True)
            logger.info(f"Docker Compose 버전: {result.stdout.strip()}")
        except FileNotFoundError:
            logger.error("Docker Compose가 설치되지 않았습니다.")
            return False

        # 필수 파일 확인
        required_files = [
            self.compose_file,
            self.project_root / "Dockerfile",
            self.project_root / "requirements.txt",
            self.project_root / ".env.example"
        ]

        for file_path in required_files:
            if not file_path.exists():
                logger.error(f"필수 파일이 없습니다: {file_path}")
                return False

        # .env 파일 생성 (없는 경우)
        env_file = self.project_root / ".env"
        if not env_file.exists():
            logger.info(".env 파일 생성 중...")
            import shutil
            shutil.copy(self.project_root / ".env.example", env_file)

        logger.info("환경 검증 완료")
        return True

    def _setup_docker_environment(self) -> bool:
        """Docker 환경 설정"""
        logger.info("Docker 환경 설정 중...")

        try:
            # 기존 컨테이너 정리
            self._cleanup()

            # Docker Compose 빌드
            logger.info("Docker 이미지 빌드 중...")
            result = subprocess.run([
                'docker-compose', '-f', str(self.compose_file),
                'build', '--no-cache'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Docker 빌드 실패: {result.stderr}")
                return False

            # Docker Compose 시작
            logger.info("Docker 서비스 시작 중...")
            result = subprocess.run([
                'docker-compose', '-f', str(self.compose_file),
                'up', '-d'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"Docker 서비스 시작 실패: {result.stderr}")
                return False

            logger.info("Docker 환경 설정 완료")
            return True

        except Exception as e:
            logger.error(f"Docker 환경 설정 오류: {e}")
            return False

    def _wait_for_services(self, timeout: int = 120) -> bool:
        """서비스 준비 대기"""
        logger.info("서비스 준비 대기 중...")

        services = {
            'web': f"{self.base_url}/api/download/health",
            'redis': self._check_redis_health,
            'postgres': self._check_postgres_health
        }

        start_time = time.time()

        while time.time() - start_time < timeout:
            all_ready = True

            for service_name, check in services.items():
                try:
                    if callable(check):
                        if not check():
                            all_ready = False
                            break
                    else:
                        response = requests.get(check, timeout=5)
                        if response.status_code != 200:
                            all_ready = False
                            break
                except Exception:
                    all_ready = False
                    break

            if all_ready:
                logger.info("모든 서비스 준비 완료")
                return True

            logger.info("서비스 준비 대기 중... (10초 후 재시도)")
            time.sleep(10)

        logger.error("서비스 준비 타임아웃")
        return False

    def _check_redis_health(self) -> bool:
        """Redis 헬스 체크"""
        try:
            result = subprocess.run([
                'docker-compose', 'exec', '-T', 'redis',
                'redis-cli', 'ping'
            ], cwd=self.project_root, capture_output=True, text=True)
            return result.returncode == 0 and 'PONG' in result.stdout
        except Exception:
            return False

    def _check_postgres_health(self) -> bool:
        """PostgreSQL 헬스 체크"""
        try:
            result = subprocess.run([
                'docker-compose', 'exec', '-T', 'postgres',
                'pg_isready', '-U', 'k_ocr_user'
            ], cwd=self.project_root, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _run_functional_tests(self) -> bool:
        """기능 테스트 실행"""
        logger.info("기능 테스트 실행 중...")

        test_cases = [
            ("헬스 체크", self._test_health_endpoint),
            ("정적 파일", self._test_static_files),
            ("메인 페이지", self._test_main_page),
            ("파일 업로드", self._test_file_upload),
            ("API 엔드포인트", self._test_api_endpoints),
        ]

        passed = 0
        for test_name, test_func in test_cases:
            logger.info(f"테스트: {test_name}")
            try:
                result = test_func()
                if result:
                    logger.info(f"✅ {test_name} 통과")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name} 실패")

                self.test_results.append({
                    'test': test_name,
                    'status': 'PASS' if result else 'FAIL',
                    'category': 'functional'
                })
            except Exception as e:
                logger.error(f"❌ {test_name} 오류: {e}")
                self.test_results.append({
                    'test': test_name,
                    'status': 'ERROR',
                    'error': str(e),
                    'category': 'functional'
                })

        success_rate = passed / len(test_cases)
        logger.info(f"기능 테스트 결과: {passed}/{len(test_cases)} ({success_rate:.1%})")
        return success_rate >= 0.8  # 80% 이상 통과 필요

    def _test_health_endpoint(self) -> bool:
        """헬스 체크 엔드포인트 테스트"""
        try:
            response = requests.get(f"{self.base_url}/api/download/health", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def _test_static_files(self) -> bool:
        """정적 파일 테스트"""
        try:
            # CSS 파일 확인
            response = requests.get(f"{self.base_url}/static/css/main.css", timeout=10)
            if response.status_code != 200:
                return False

            # JS 파일 확인
            response = requests.get(f"{self.base_url}/static/js/main.js", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def _test_main_page(self) -> bool:
        """메인 페이지 테스트"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code != 200:
                return False

            # 필수 요소 확인
            content = response.text
            required_elements = [
                'K-OCR',
                'upload',
                'drag',
                'drop'
            ]

            return all(element in content.lower() for element in required_elements)
        except Exception:
            return False

    def _test_file_upload(self) -> bool:
        """파일 업로드 테스트"""
        try:
            # 테스트용 PDF 파일 생성 (간단한 텍스트)
            import tempfile
            from reportlab.pdfgen import canvas

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                c = canvas.Canvas(tmp_file.name)
                c.drawString(100, 750, "Test PDF for K-OCR")
                c.save()

                # 파일 업로드 시도
                with open(tmp_file.name, 'rb') as f:
                    files = {'file': ('test.pdf', f, 'application/pdf')}
                    response = requests.post(
                        f"{self.base_url}/api/upload",
                        files=files,
                        timeout=30
                    )

                os.unlink(tmp_file.name)
                return response.status_code in [200, 201]

        except Exception:
            return False

    def _test_api_endpoints(self) -> bool:
        """API 엔드포인트 테스트"""
        try:
            # API 문서 확인
            response = requests.get(f"{self.base_url}/api/docs", timeout=10)
            if response.status_code != 200:
                return False

            # 메트릭스 엔드포인트 확인 (있는 경우)
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            # 메트릭스는 선택사항이므로 404도 허용
            return response.status_code in [200, 404]
        except Exception:
            return False

    def _run_performance_tests(self) -> bool:
        """성능 테스트 실행"""
        logger.info("성능 테스트 실행 중...")

        try:
            # 동시 요청 테스트
            import concurrent.futures
            import threading

            def make_request():
                try:
                    response = requests.get(f"{self.base_url}/api/download/health", timeout=5)
                    return response.status_code == 200
                except Exception:
                    return False

            # 10개 동시 요청
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                start_time = time.time()
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                end_time = time.time()

            duration = end_time - start_time
            success_count = sum(results)
            success_rate = success_count / len(results)

            logger.info(f"동시 요청 테스트: {success_count}/10 성공 ({success_rate:.1%}), {duration:.2f}초")

            self.test_results.append({
                'test': 'concurrent_requests',
                'success_rate': success_rate,
                'duration': duration,
                'category': 'performance'
            })

            # 응답 시간 테스트
            response_times = []
            for _ in range(5):
                start_time = time.time()
                response = requests.get(f"{self.base_url}/api/download/health", timeout=10)
                end_time = time.time()
                if response.status_code == 200:
                    response_times.append(end_time - start_time)

            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                logger.info(f"평균 응답 시간: {avg_response_time:.3f}초")

                self.test_results.append({
                    'test': 'response_time',
                    'avg_time': avg_response_time,
                    'category': 'performance'
                })

                return success_rate >= 0.8 and avg_response_time < 2.0

            return False

        except Exception as e:
            logger.error(f"성능 테스트 오류: {e}")
            return False

    def _check_resource_usage(self) -> bool:
        """리소스 사용량 체크"""
        logger.info("리소스 사용량 체크 중...")

        try:
            # Docker 컨테이너 상태 확인
            containers = self.docker_client.containers.list()

            total_memory_usage = 0
            total_cpu_usage = 0
            container_stats = []

            for container in containers:
                if 'k-ocr' in container.name or any(name in container.name.lower()
                    for name in ['web', 'worker', 'redis', 'postgres']):

                    stats = container.stats(stream=False)

                    # 메모리 사용량 (MB)
                    memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)
                    total_memory_usage += memory_usage

                    # CPU 사용량 (%)
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               stats['precpu_stats']['cpu_usage']['total_usage']
                    system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                      stats['precpu_stats']['system_cpu_usage']
                    cpu_usage = (cpu_delta / system_cpu_delta) * 100.0 if system_cpu_delta > 0 else 0
                    total_cpu_usage += cpu_usage

                    container_stats.append({
                        'name': container.name,
                        'memory_mb': memory_usage,
                        'cpu_percent': cpu_usage
                    })

                    logger.info(f"{container.name}: Memory={memory_usage:.1f}MB, CPU={cpu_usage:.1f}%")

            logger.info(f"전체 리소스 사용량: Memory={total_memory_usage:.1f}MB, CPU={total_cpu_usage:.1f}%")

            self.test_results.append({
                'test': 'resource_usage',
                'total_memory_mb': total_memory_usage,
                'total_cpu_percent': total_cpu_usage,
                'containers': container_stats,
                'category': 'resource'
            })

            # 리소스 사용량 임계값 체크 (개발 환경 기준)
            return total_memory_usage < 2048 and total_cpu_usage < 200  # 2GB, 200% CPU

        except Exception as e:
            logger.error(f"리소스 사용량 체크 오류: {e}")
            return False

    def _validate_logs(self) -> bool:
        """로그 검증"""
        logger.info("로그 검증 중...")

        try:
            # Docker Compose 로그 확인
            result = subprocess.run([
                'docker-compose', 'logs', '--tail=50'
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error("로그 수집 실패")
                return False

            logs = result.stdout

            # 오류 로그 검사
            error_patterns = [
                'ERROR',
                'CRITICAL',
                'FATAL',
                'Exception',
                'Traceback'
            ]

            error_count = 0
            for pattern in error_patterns:
                error_count += logs.count(pattern)

            logger.info(f"로그에서 발견된 오류: {error_count}개")

            # 정상 동작 로그 검사
            success_patterns = [
                'Application startup complete',
                'server started',
                'ready to accept connections',
                'Connected to database'
            ]

            success_count = 0
            for pattern in success_patterns:
                if pattern.lower() in logs.lower():
                    success_count += 1

            logger.info(f"정상 동작 로그: {success_count}개")

            self.test_results.append({
                'test': 'log_validation',
                'error_count': error_count,
                'success_indicators': success_count,
                'category': 'validation'
            })

            return error_count < 5 and success_count > 0

        except Exception as e:
            logger.error(f"로그 검증 오류: {e}")
            return False

    def _cleanup(self):
        """환경 정리"""
        logger.info("환경 정리 중...")

        try:
            subprocess.run([
                'docker-compose', '-f', str(self.compose_file),
                'down', '-v', '--remove-orphans'
            ], cwd=self.project_root, capture_output=True)

            # 사용하지 않는 Docker 리소스 정리
            subprocess.run([
                'docker', 'system', 'prune', '-f'
            ], capture_output=True)

        except Exception as e:
            logger.error(f"정리 중 오류: {e}")

    def _print_test_summary(self):
        """테스트 결과 요약 출력"""
        logger.info("\n=== 테스트 결과 요약 ===")

        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0, 'failed': 0}

            categories[category]['total'] += 1
            if result.get('status') == 'PASS' or 'success_rate' in result:
                categories[category]['passed'] += 1
            else:
                categories[category]['failed'] += 1

        for category, stats in categories.items():
            logger.info(f"{category.upper()}: {stats['passed']}/{stats['total']} 통과")

        # 전체 결과
        total_tests = len(self.test_results)
        total_passed = sum(1 for r in self.test_results
                          if r.get('status') == 'PASS' or 'success_rate' in r)

        logger.info(f"\n전체 결과: {total_passed}/{total_tests} 통과 ({total_passed/total_tests:.1%})")

        # 테스트 결과를 JSON 파일로 저장
        results_file = self.project_root / "deploy/tests/local-test-results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': {
                    'total': total_tests,
                    'passed': total_passed,
                    'success_rate': total_passed / total_tests
                },
                'categories': categories,
                'details': self.test_results
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"상세 결과 저장: {results_file}")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='K-OCR 로컬 Docker 환경 테스트')
    parser.add_argument('--project-root', '-r', help='프로젝트 루트 디렉토리')
    parser.add_argument('--cleanup-only', '-c', action='store_true',
                       help='정리만 수행')

    args = parser.parse_args()

    tester = LocalDockerTester(args.project_root)

    if args.cleanup_only:
        tester._cleanup()
        return

    success = tester.run_all_tests()

    if not success:
        logger.error("테스트 실패")
        sys.exit(1)

    logger.info("모든 테스트 성공!")


if __name__ == '__main__':
    main()