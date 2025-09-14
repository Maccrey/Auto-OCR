"""
스트레스 및 부하 테스트 모듈

시스템의 한계와 안정성을 검증하는 테스트:
- 대용량 파일 처리 성능
- 동시 사용자 부하 테스트
- 메모리 누수 및 리소스 관리 테스트
- 장시간 실행 안정성 테스트
"""

import asyncio
import gc
import os
import psutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw

# 실제 구현된 모듈들
from backend.utils.temp_storage import TempStorage
from backend.core.image_processor import ImageProcessor, ProcessingOptions


class PerformanceMonitor:
    """성능 모니터링 유틸리티"""

    def __init__(self):
        self.metrics = {}
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        self.peak_memory = self.initial_memory

    def start_timer(self, operation: str):
        """타이머 시작"""
        self.metrics[operation] = {
            'start_time': time.time(),
            'start_memory': self.process.memory_info().rss
        }

    def end_timer(self, operation: str) -> Dict:
        """타이머 종료 및 메트릭 수집"""
        if operation not in self.metrics:
            return {}

        current_memory = self.process.memory_info().rss
        self.peak_memory = max(self.peak_memory, current_memory)

        end_time = time.time()
        duration = end_time - self.metrics[operation]['start_time']
        memory_delta = current_memory - self.metrics[operation]['start_memory']

        result = {
            'duration': duration,
            'memory_used': memory_delta,
            'peak_memory': self.peak_memory,
            'cpu_percent': self.process.cpu_percent()
        }

        self.metrics[operation].update(result)
        return result

    def get_system_stats(self) -> Dict:
        """시스템 상태 정보 수집"""
        return {
            'memory_usage_mb': self.process.memory_info().rss / 1024 / 1024,
            'memory_percent': self.process.memory_percent(),
            'cpu_percent': self.process.cpu_percent(),
            'num_threads': self.process.num_threads(),
            'open_files': len(self.process.open_files()),
            'total_memory_increase_mb': (self.peak_memory - self.initial_memory) / 1024 / 1024
        }

    def assert_memory_limit(self, limit_mb: int):
        """메모리 사용량 임계값 검증"""
        current_mb = self.process.memory_info().rss / 1024 / 1024
        assert current_mb < limit_mb, f"Memory usage {current_mb:.1f}MB exceeds limit {limit_mb}MB"

    def force_gc(self):
        """가비지 컬렉션 강제 실행"""
        gc.collect()


@pytest.fixture
def performance_monitor():
    """성능 모니터 픽스처"""
    return PerformanceMonitor()


@pytest.fixture
def test_data_dir():
    """테스트 데이터 디렉토리"""
    test_dir = Path(tempfile.mkdtemp(prefix="stress_test_"))
    yield test_dir

    # 정리
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def temp_storage(test_data_dir):
    """임시 저장소"""
    storage_dir = test_data_dir / "temp_storage"
    storage_dir.mkdir()
    return TempStorage(str(storage_dir))


@pytest.fixture
def image_processor():
    """이미지 프로세서"""
    return ImageProcessor()


class TestStressAndLoad:
    """스트레스 및 부하 테스트"""

    def create_test_image(self, size: Tuple[int, int], text: str = "Test") -> bytes:
        """테스트 이미지 생성"""
        img = Image.new('RGB', size, color='white')
        draw = ImageDraw.Draw(img)

        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
        except:
            font = None

        draw.text((50, 50), text, fill='black', font=font)

        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()

    def test_large_file_processing(self, temp_storage, image_processor,
                                   performance_monitor, test_data_dir):
        """대용량 파일 처리 테스트"""
        print("\n=== Large File Processing Test ===")

        # 다양한 크기의 이미지 생성 및 처리
        test_sizes = [
            (1920, 1080, "2MP"),
            (2560, 1440, "3.7MP"),
            (3840, 2160, "8.3MP"),
            (5120, 2880, "14.7MP")
        ]

        processing_options = ProcessingOptions(
            apply_clahe=True,
            deskew_enabled=True,
            noise_removal=True,
            adaptive_threshold=True
        )

        results = []

        for width, height, label in test_sizes:
            print(f"\nTesting {label} image ({width}x{height})...")

            # 이미지 생성
            img_data = self.create_test_image((width, height), f"Large image test {label}")
            img_path = test_data_dir / f"large_{label.replace('.', '_')}.png"

            with open(img_path, 'wb') as f:
                f.write(img_data)

            file_size_mb = len(img_data) / 1024 / 1024

            # 성능 측정
            performance_monitor.start_timer(f"process_{label}")

            try:
                processed_path = image_processor.preprocess_pipeline(
                    str(img_path), processing_options
                )

                metrics = performance_monitor.end_timer(f"process_{label}")

                # 결과 저장
                results.append({
                    'label': label,
                    'size': (width, height),
                    'file_size_mb': file_size_mb,
                    'processing_time': metrics['duration'],
                    'memory_used_mb': metrics['memory_used'] / 1024 / 1024,
                    'throughput_mb_per_sec': file_size_mb / metrics['duration'] if metrics['duration'] > 0 else 0,
                    'success': True
                })

                print(f"  ✓ Processed in {metrics['duration']:.2f}s")
                print(f"  ✓ Memory used: {metrics['memory_used'] / 1024 / 1024:.1f}MB")
                print(f"  ✓ Throughput: {file_size_mb / metrics['duration']:.1f} MB/s")

                # 처리된 파일 정리
                if processed_path and os.path.exists(processed_path):
                    os.remove(processed_path)

            except Exception as e:
                print(f"  ✗ Failed: {e}")
                results.append({
                    'label': label,
                    'success': False,
                    'error': str(e)
                })

            # 메모리 정리
            performance_monitor.force_gc()

        # 결과 분석
        print(f"\n=== Large File Processing Results ===")
        successful = [r for r in results if r.get('success', False)]

        if successful:
            avg_time = sum(r['processing_time'] for r in successful) / len(successful)
            avg_throughput = sum(r['throughput_mb_per_sec'] for r in successful) / len(successful)

            print(f"Successful processes: {len(successful)}/{len(results)}")
            print(f"Average processing time: {avg_time:.2f}s")
            print(f"Average throughput: {avg_throughput:.1f} MB/s")

            # 성능 검증 - 14.7MP 이미지도 30초 이내에 처리되어야 함
            for result in successful:
                assert result['processing_time'] < 30.0, \
                    f"Processing time {result['processing_time']:.2f}s too slow for {result['label']}"

        print("=== Large File Processing Test Completed ===\n")

    def test_concurrent_users_simulation(self, temp_storage, image_processor,
                                         performance_monitor, test_data_dir):
        """동시 사용자 시뮬레이션 테스트"""
        print("\n=== Concurrent Users Simulation Test ===")

        # 테스트 설정
        num_users = 5
        requests_per_user = 3
        total_requests = num_users * requests_per_user

        # 테스트 이미지 생성
        test_images = []
        for i in range(total_requests):
            img_data = self.create_test_image((800, 600), f"Concurrent test {i}")
            img_path = test_data_dir / f"concurrent_{i}.png"
            with open(img_path, 'wb') as f:
                f.write(img_data)
            test_images.append(img_path)

        processing_options = ProcessingOptions(apply_clahe=True)

        def user_simulation(user_id: int) -> List[Dict]:
            """단일 사용자 시뮬레이션"""
            user_results = []

            for req_id in range(requests_per_user):
                img_index = user_id * requests_per_user + req_id
                img_path = test_images[img_index]

                start_time = time.time()
                try:
                    processed_path = image_processor.preprocess_pipeline(
                        str(img_path), processing_options
                    )

                    duration = time.time() - start_time
                    user_results.append({
                        'user_id': user_id,
                        'request_id': req_id,
                        'duration': duration,
                        'success': True,
                        'processed_path': processed_path
                    })

                except Exception as e:
                    duration = time.time() - start_time
                    user_results.append({
                        'user_id': user_id,
                        'request_id': req_id,
                        'duration': duration,
                        'success': False,
                        'error': str(e)
                    })

            return user_results

        # 동시 사용자 실행
        performance_monitor.start_timer("concurrent_simulation")

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_simulation, user_id) for user_id in range(num_users)]
            all_results = []

            for future in as_completed(futures):
                user_results = future.result()
                all_results.extend(user_results)

        total_metrics = performance_monitor.end_timer("concurrent_simulation")

        # 결과 분석
        successful_requests = [r for r in all_results if r['success']]
        failed_requests = [r for r in all_results if not r['success']]

        success_rate = len(successful_requests) / len(all_results)

        if successful_requests:
            avg_response_time = sum(r['duration'] for r in successful_requests) / len(successful_requests)
            max_response_time = max(r['duration'] for r in successful_requests)
            min_response_time = min(r['duration'] for r in successful_requests)
        else:
            avg_response_time = max_response_time = min_response_time = 0

        print(f"=== Concurrent Test Results ===")
        print(f"Total requests: {len(all_results)}")
        print(f"Successful: {len(successful_requests)} ({success_rate:.1%})")
        print(f"Failed: {len(failed_requests)}")
        print(f"Total execution time: {total_metrics['duration']:.2f}s")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Min/Max response time: {min_response_time:.3f}s / {max_response_time:.3f}s")
        print(f"Requests per second: {len(all_results) / total_metrics['duration']:.1f}")

        # 성능 검증
        assert success_rate >= 0.8, f"Success rate {success_rate:.1%} too low"
        assert avg_response_time < 5.0, f"Average response time {avg_response_time:.2f}s too slow"

        # 처리된 파일들 정리
        for result in successful_requests:
            if result.get('processed_path') and os.path.exists(result['processed_path']):
                os.remove(result['processed_path'])

        print("=== Concurrent Users Simulation Test Completed ===\n")

    def test_memory_stress_test(self, temp_storage, image_processor,
                                performance_monitor, test_data_dir):
        """메모리 스트레스 테스트"""
        print("\n=== Memory Stress Test ===")

        # 초기 메모리 상태 기록
        initial_stats = performance_monitor.get_system_stats()
        print(f"Initial memory: {initial_stats['memory_usage_mb']:.1f}MB")

        processing_options = ProcessingOptions(
            apply_clahe=True,
            deskew_enabled=True,
            noise_removal=True,
            adaptive_threshold=True
        )

        processed_files = []
        memory_snapshots = []

        # 연속으로 많은 이미지 처리
        for i in range(20):  # 20개 이미지 처리
            print(f"Processing image {i+1}/20...")

            # 다양한 크기의 이미지 생성
            size = (800 + i * 100, 600 + i * 50)  # 점점 큰 이미지
            img_data = self.create_test_image(size, f"Stress test {i}")
            img_path = test_data_dir / f"stress_{i}.png"

            with open(img_path, 'wb') as f:
                f.write(img_data)

            try:
                processed_path = image_processor.preprocess_pipeline(
                    str(img_path), processing_options
                )

                if processed_path:
                    processed_files.append(processed_path)

                # 메모리 상태 기록
                current_stats = performance_monitor.get_system_stats()
                memory_snapshots.append({
                    'iteration': i,
                    'memory_mb': current_stats['memory_usage_mb'],
                    'memory_increase_mb': current_stats['total_memory_increase_mb']
                })

                print(f"  Memory: {current_stats['memory_usage_mb']:.1f}MB "
                      f"(+{current_stats['total_memory_increase_mb']:.1f}MB)")

            except Exception as e:
                print(f"  Failed: {e}")

            # 중간에 가비지 컬렉션 (10번째 이후)
            if i > 10:
                performance_monitor.force_gc()

        # 최종 정리
        for processed_file in processed_files:
            if os.path.exists(processed_file):
                os.remove(processed_file)

        performance_monitor.force_gc()

        # 최종 메모리 상태
        final_stats = performance_monitor.get_system_stats()

        print(f"\n=== Memory Stress Test Results ===")
        print(f"Initial memory: {initial_stats['memory_usage_mb']:.1f}MB")
        print(f"Peak memory: {performance_monitor.peak_memory / 1024 / 1024:.1f}MB")
        print(f"Final memory: {final_stats['memory_usage_mb']:.1f}MB")
        print(f"Net increase: {final_stats['total_memory_increase_mb']:.1f}MB")

        # 메모리 누수 검증 - 최종 메모리 증가가 200MB 이하여야 함
        assert final_stats['total_memory_increase_mb'] < 200, \
            f"Memory leak detected: {final_stats['total_memory_increase_mb']:.1f}MB increase"

        print("=== Memory Stress Test Completed ===\n")

    def test_sustained_load_test(self, temp_storage, image_processor,
                                 performance_monitor, test_data_dir):
        """지속적 부하 테스트"""
        print("\n=== Sustained Load Test ===")

        # 테스트 설정
        test_duration = 30  # 30초 동안
        target_rps = 2      # 초당 2요청 목표

        processing_options = ProcessingOptions(apply_clahe=True)

        # 테스트 이미지 준비
        img_data = self.create_test_image((600, 400), "Sustained load test")
        img_path = test_data_dir / "sustained_test.png"
        with open(img_path, 'wb') as f:
            f.write(img_data)

        results = []
        start_time = time.time()
        request_count = 0

        performance_monitor.start_timer("sustained_load")

        print(f"Running sustained load for {test_duration} seconds at {target_rps} RPS...")

        while time.time() - start_time < test_duration:
            request_start = time.time()

            try:
                processed_path = image_processor.preprocess_pipeline(
                    str(img_path), processing_options
                )

                request_duration = time.time() - request_start
                results.append({
                    'request_id': request_count,
                    'duration': request_duration,
                    'timestamp': time.time(),
                    'success': True
                })

                if processed_path and os.path.exists(processed_path):
                    os.remove(processed_path)

            except Exception as e:
                request_duration = time.time() - request_start
                results.append({
                    'request_id': request_count,
                    'duration': request_duration,
                    'timestamp': time.time(),
                    'success': False,
                    'error': str(e)
                })

            request_count += 1

            # 요청 간격 조절
            sleep_time = 1.0 / target_rps - request_duration
            if sleep_time > 0:
                time.sleep(sleep_time)

        total_metrics = performance_monitor.end_timer("sustained_load")

        # 결과 분석
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]

        actual_rps = len(results) / total_metrics['duration']
        success_rate = len(successful_requests) / len(results) if results else 0

        if successful_requests:
            avg_response_time = sum(r['duration'] for r in successful_requests) / len(successful_requests)
            response_times = [r['duration'] for r in successful_requests]
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response_time = p95_response_time = 0

        print(f"\n=== Sustained Load Test Results ===")
        print(f"Test duration: {total_metrics['duration']:.1f}s")
        print(f"Total requests: {len(results)}")
        print(f"Successful: {len(successful_requests)} ({success_rate:.1%})")
        print(f"Failed: {len(failed_requests)}")
        print(f"Actual RPS: {actual_rps:.1f}")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"95th percentile response time: {p95_response_time:.3f}s")

        # 성능 검증
        assert success_rate >= 0.95, f"Success rate {success_rate:.1%} too low for sustained load"
        assert actual_rps >= target_rps * 0.8, f"Actual RPS {actual_rps:.1f} too low (target: {target_rps})"

        print("=== Sustained Load Test Completed ===\n")

    def test_resource_exhaustion_recovery(self, temp_storage, performance_monitor, test_data_dir):
        """리소스 고갈 및 복구 테스트"""
        print("\n=== Resource Exhaustion Recovery Test ===")

        # 대량의 파일 생성으로 저장소 스트레스
        file_ids = []

        try:
            # 대량 파일 저장
            for i in range(100):
                file_content = f"Stress test file {i}" * 1000  # ~17KB per file
                file_id = temp_storage.save_file(
                    file_content.encode(),
                    filename=f"stress_{i}.txt",
                    uploader_id="stress_test_user"
                )
                file_ids.append(file_id)

                if i % 20 == 0:
                    stats = performance_monitor.get_system_stats()
                    print(f"Created {i} files, memory: {stats['memory_usage_mb']:.1f}MB")

            print(f"Successfully created {len(file_ids)} files")

            # 파일 접근 테스트
            access_success = 0
            for file_id in file_ids[:10]:  # 처음 10개 파일만 테스트
                file_info = temp_storage.get_file(file_id, "stress_test_user")
                if file_info:
                    access_success += 1

            print(f"Successfully accessed {access_success}/10 files")

            # 시스템이 여전히 응답하는지 확인
            assert access_success >= 8, "Too many file access failures"

        finally:
            # 정리 - 강제 만료
            cleaned = temp_storage.cleanup_expired_files(current_time=time.time() + 86401)
            print(f"Cleaned up {cleaned} files")

            # 메모리 정리
            performance_monitor.force_gc()

            final_stats = performance_monitor.get_system_stats()
            print(f"Final memory: {final_stats['memory_usage_mb']:.1f}MB")

        print("=== Resource Exhaustion Recovery Test Completed ===\n")


class TestPerformanceBenchmarks:
    """성능 벤치마크 테스트"""

    def test_processing_speed_benchmark(self, image_processor, performance_monitor, test_data_dir):
        """이미지 처리 속도 벤치마크"""
        print("\n=== Processing Speed Benchmark ===")

        # 벤치마크 이미지 생성
        benchmark_image = Image.new('RGB', (1920, 1080), color='white')
        draw = ImageDraw.Draw(benchmark_image)

        # 복잡한 텍스트 패턴 추가
        for i in range(20):
            y_pos = 50 + i * 40
            draw.text((50, y_pos), f"Benchmark line {i+1}: The quick brown fox jumps over the lazy dog.", fill='black')

        img_path = test_data_dir / "benchmark.png"
        benchmark_image.save(img_path)

        # 다양한 처리 옵션 테스트
        test_configurations = [
            ("Minimal", ProcessingOptions(apply_clahe=False, deskew_enabled=False, noise_removal=False, adaptive_threshold=False)),
            ("Basic", ProcessingOptions(apply_clahe=True, deskew_enabled=False, noise_removal=False, adaptive_threshold=True)),
            ("Standard", ProcessingOptions(apply_clahe=True, deskew_enabled=True, noise_removal=False, adaptive_threshold=True)),
            ("Full", ProcessingOptions(apply_clahe=True, deskew_enabled=True, noise_removal=True, adaptive_threshold=True))
        ]

        benchmark_results = []

        for config_name, options in test_configurations:
            print(f"\nTesting {config_name} configuration...")

            performance_monitor.start_timer(f"benchmark_{config_name}")

            try:
                processed_path = image_processor.preprocess_pipeline(str(img_path), options)
                metrics = performance_monitor.end_timer(f"benchmark_{config_name}")

                benchmark_results.append({
                    'configuration': config_name,
                    'duration': metrics['duration'],
                    'memory_used_mb': metrics['memory_used'] / 1024 / 1024,
                    'success': True
                })

                print(f"  Time: {metrics['duration']:.3f}s")
                print(f"  Memory: {metrics['memory_used'] / 1024 / 1024:.1f}MB")

                if processed_path and os.path.exists(processed_path):
                    os.remove(processed_path)

            except Exception as e:
                benchmark_results.append({
                    'configuration': config_name,
                    'success': False,
                    'error': str(e)
                })
                print(f"  Failed: {e}")

        # 벤치마크 결과 분석
        print(f"\n=== Benchmark Results ===")
        successful_configs = [r for r in benchmark_results if r['success']]

        if successful_configs:
            fastest = min(successful_configs, key=lambda x: x['duration'])
            slowest = max(successful_configs, key=lambda x: x['duration'])

            print(f"Fastest: {fastest['configuration']} ({fastest['duration']:.3f}s)")
            print(f"Slowest: {slowest['configuration']} ({slowest['duration']:.3f}s)")
            print(f"Speed difference: {slowest['duration'] / fastest['duration']:.1f}x")

            # 모든 설정이 합리적인 시간 내에 처리되어야 함
            for result in successful_configs:
                assert result['duration'] < 10.0, \
                    f"{result['configuration']} too slow: {result['duration']:.2f}s"

        print("=== Processing Speed Benchmark Completed ===\n")


if __name__ == "__main__":
    # 단독 실행 시 기본 스트레스 테스트
    monitor = PerformanceMonitor()

    # 간단한 메모리 테스트
    print("Running basic stress test...")

    data_list = []
    for i in range(1000):
        data_list.append(f"Test data {i}" * 100)

    stats_before = monitor.get_system_stats()

    # 가비지 컬렉션
    monitor.force_gc()
    del data_list

    stats_after = monitor.get_system_stats()

    print(f"Memory before: {stats_before['memory_usage_mb']:.1f}MB")
    print(f"Memory after: {stats_after['memory_usage_mb']:.1f}MB")
    print("Basic stress test completed!")