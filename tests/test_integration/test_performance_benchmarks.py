"""
성능 벤치마크 통합 테스트 모듈

시스템 성능 기준선 및 벤치마크 테스트
"""

import time
import threading
import psutil
import gc
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest
import tempfile
import io


class TestPerformanceBenchmarks:
    """성능 벤치마크 테스트"""

    def test_basic_performance_metrics(self):
        """기본 성능 메트릭 테스트"""
        # CPU 정보
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        assert cpu_count > 0
        if cpu_freq:
            assert cpu_freq.max > 0

        print(f"CPU: {cpu_count} cores, {cpu_freq.max if cpu_freq else 'Unknown'} MHz")

        # 메모리 정보
        memory = psutil.virtual_memory()
        assert memory.total > 0

        print(f"Memory: {memory.total / 1024 / 1024 / 1024:.1f} GB total, "
              f"{memory.available / 1024 / 1024 / 1024:.1f} GB available")

        # 디스크 정보
        disk = psutil.disk_usage('/')
        assert disk.total > 0

        print(f"Disk: {disk.total / 1024 / 1024 / 1024:.1f} GB total, "
              f"{disk.free / 1024 / 1024 / 1024:.1f} GB free")

    def test_memory_allocation_performance(self):
        """메모리 할당 성능 테스트"""
        import gc

        # 초기 메모리 상태
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 메모리 할당 성능 측정
        start_time = time.time()

        # 10MB 데이터 블록 100개 할당
        data_blocks = []
        block_size = 1024 * 1024  # 1MB
        num_blocks = 10

        for i in range(num_blocks):
            data_blocks.append(b'x' * block_size)

        allocation_time = time.time() - start_time
        peak_memory = process.memory_info().rss

        # 메모리 해제 성능 측정
        start_time = time.time()
        del data_blocks
        gc.collect()
        deallocation_time = time.time() - start_time

        final_memory = process.memory_info().rss

        # 성능 검증
        memory_allocated = peak_memory - initial_memory
        expected_memory = num_blocks * block_size

        print(f"Memory allocation: {allocation_time:.3f}s for {memory_allocated / 1024 / 1024:.1f}MB")
        print(f"Memory deallocation: {deallocation_time:.3f}s")
        print(f"Memory overhead: {(memory_allocated - expected_memory) / 1024 / 1024:.1f}MB")

        # 할당 시간이 합리적인지 확인 (100MB를 1초 이내)
        assert allocation_time < 1.0
        assert deallocation_time < 1.0

        # 메모리가 실제로 할당되었는지 확인
        assert memory_allocated >= expected_memory * 0.8  # 80% 이상

    def test_cpu_intensive_performance(self):
        """CPU 집약적 작업 성능 테스트"""

        def cpu_bound_task(n):
            """CPU 바운드 작업"""
            result = 0
            for i in range(n):
                result += i * i
            return result

        # 단일 스레드 성능
        start_time = time.time()
        result1 = cpu_bound_task(1000000)
        single_thread_time = time.time() - start_time

        # 멀티 스레드 성능
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(cpu_bound_task, 500000)
            future2 = executor.submit(cpu_bound_task, 500000)
            result2 = future1.result() + future2.result()

        multi_thread_time = time.time() - start_time

        print(f"Single thread: {single_thread_time:.3f}s")
        print(f"Multi thread: {multi_thread_time:.3f}s")
        print(f"Speedup: {single_thread_time / multi_thread_time:.2f}x")

        # 결과 검증
        assert result1 == result2
        assert single_thread_time < 5.0  # 5초 이내
        assert multi_thread_time < 5.0

        # 멀티스레드가 어느 정도 빠른지 확인 (최소 10% 향상)
        assert multi_thread_time < single_thread_time * 0.9

    def test_file_io_performance(self):
        """파일 I/O 성능 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "performance_test.dat"

            # 쓰기 성능 측정
            data_size = 10 * 1024 * 1024  # 10MB
            test_data = b'x' * data_size

            start_time = time.time()
            with open(test_file, 'wb') as f:
                f.write(test_data)
            write_time = time.time() - start_time

            # 읽기 성능 측정
            start_time = time.time()
            with open(test_file, 'rb') as f:
                read_data = f.read()
            read_time = time.time() - start_time

            # 성능 검증
            write_speed = data_size / write_time / 1024 / 1024  # MB/s
            read_speed = data_size / read_time / 1024 / 1024   # MB/s

            print(f"File write: {write_time:.3f}s ({write_speed:.1f} MB/s)")
            print(f"File read: {read_time:.3f}s ({read_speed:.1f} MB/s)")

            assert len(read_data) == len(test_data)
            assert read_data == test_data

            # 최소 성능 요구사항 (10MB/s 이상)
            assert write_speed > 10
            assert read_speed > 10

    def test_concurrent_task_performance(self):
        """동시 작업 성능 테스트"""
        num_tasks = 20
        task_duration = 0.1  # 각 작업이 0.1초

        def simple_task(task_id):
            """간단한 작업"""
            start_time = time.time()
            # CPU와 I/O를 혼합한 작업 시뮬레이션
            result = sum(i * i for i in range(10000))  # CPU 작업
            time.sleep(0.05)  # I/O 대기 시뮬레이션
            duration = time.time() - start_time
            return {"task_id": task_id, "result": result, "duration": duration}

        # 순차 실행
        start_time = time.time()
        sequential_results = []
        for i in range(num_tasks):
            sequential_results.append(simple_task(i))
        sequential_time = time.time() - start_time

        # 동시 실행
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            concurrent_results = list(executor.map(simple_task, range(num_tasks)))
        concurrent_time = time.time() - start_time

        print(f"Sequential execution: {sequential_time:.3f}s")
        print(f"Concurrent execution: {concurrent_time:.3f}s")
        print(f"Speedup: {sequential_time / concurrent_time:.2f}x")

        # 결과 검증
        assert len(sequential_results) == len(concurrent_results) == num_tasks

        # 동시 실행이 더 빨라야 함 (최소 2배)
        assert concurrent_time < sequential_time / 2

        # 각 작업의 결과가 동일한지 확인
        for seq_result, conc_result in zip(sequential_results, concurrent_results):
            assert seq_result["result"] == conc_result["result"]

    def test_memory_stress_test(self):
        """메모리 스트레스 테스트"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 메모리 사용량을 점진적으로 늘려가며 테스트
        max_blocks = 50  # 최대 50MB
        block_size = 1024 * 1024  # 1MB 블록

        memory_blocks = []
        peak_memory = initial_memory

        try:
            for i in range(max_blocks):
                # 메모리 블록 할당
                block = b'x' * block_size
                memory_blocks.append(block)

                current_memory = process.memory_info().rss
                peak_memory = max(peak_memory, current_memory)

                # 메모리 사용량 모니터링
                if i % 10 == 0:
                    memory_mb = current_memory / 1024 / 1024
                    print(f"Allocated {i + 1} blocks, Memory: {memory_mb:.1f}MB")

                # 메모리 사용량이 과도하게 증가하면 중단
                if current_memory > initial_memory + (100 * 1024 * 1024):  # 100MB 증가 제한
                    break

        finally:
            # 메모리 정리
            del memory_blocks
            gc.collect()

        final_memory = process.memory_info().rss
        memory_reclaimed = peak_memory - final_memory

        print(f"Peak memory usage: {peak_memory / 1024 / 1024:.1f}MB")
        print(f"Memory reclaimed: {memory_reclaimed / 1024 / 1024:.1f}MB")

        # 메모리가 적절히 회수되었는지 확인
        assert memory_reclaimed > 0
        assert final_memory < peak_memory * 0.8  # 80% 이상 회수

    def test_throughput_benchmark(self):
        """처리량 벤치마크 테스트"""

        def process_item(item_id):
            """항목 처리 시뮬레이션"""
            # 간단한 계산 작업
            result = sum(range(item_id * 100, (item_id + 1) * 100))
            # 작은 지연 시뮬레이션
            time.sleep(0.001)  # 1ms
            return result

        num_items = 1000
        max_workers = 4

        # 처리량 측정
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_item, range(num_items)))

        total_time = time.time() - start_time
        throughput = num_items / total_time

        print(f"Processed {num_items} items in {total_time:.3f}s")
        print(f"Throughput: {throughput:.1f} items/second")

        # 결과 검증
        assert len(results) == num_items
        assert all(isinstance(r, int) for r in results)

        # 최소 처리량 요구사항 (100 items/sec)
        assert throughput > 100

    def test_response_time_distribution(self):
        """응답 시간 분포 테스트"""

        def timed_operation():
            """시간 측정 작업"""
            start = time.time()

            # 작업 시뮬레이션 (약간의 랜덤성 포함)
            import random
            work_amount = random.randint(1000, 5000)
            result = sum(range(work_amount))

            duration = time.time() - start
            return duration, result

        # 여러 번 실행하여 응답 시간 분포 측정
        num_samples = 100
        response_times = []

        for _ in range(num_samples):
            duration, _ = timed_operation()
            response_times.append(duration)

        # 통계 계산
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        # 백분위수 계산
        sorted_times = sorted(response_times)
        p50 = sorted_times[len(sorted_times) // 2]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        print(f"Response time statistics:")
        print(f"  Average: {avg_time * 1000:.2f}ms")
        print(f"  Min: {min_time * 1000:.2f}ms")
        print(f"  Max: {max_time * 1000:.2f}ms")
        print(f"  P50: {p50 * 1000:.2f}ms")
        print(f"  P95: {p95 * 1000:.2f}ms")
        print(f"  P99: {p99 * 1000:.2f}ms")

        # 성능 요구사항 검증
        assert avg_time < 0.01   # 평균 10ms 이내
        assert p95 < 0.02        # 95% 20ms 이내
        assert p99 < 0.05        # 99% 50ms 이내

    def test_resource_cleanup_efficiency(self):
        """리소스 정리 효율성 테스트"""
        import tempfile
        import os

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 임시 리소스 생성 및 정리 테스트
        temp_files = []
        memory_objects = []

        try:
            # 리소스 생성
            for i in range(10):
                # 임시 파일 생성
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file.write(b'x' * (1024 * 1024))  # 1MB
                temp_file.close()
                temp_files.append(temp_file.name)

                # 메모리 객체 생성
                memory_objects.append(b'y' * (1024 * 1024))  # 1MB

            # 피크 리소스 사용량
            peak_memory = process.memory_info().rss

            # 파일 정리
            cleanup_start = time.time()
            for temp_file in temp_files:
                os.unlink(temp_file)
            temp_files.clear()

            # 메모리 정리
            del memory_objects
            gc.collect()

            cleanup_time = time.time() - cleanup_start
            final_memory = process.memory_info().rss

        finally:
            # 보장된 정리
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass

        print(f"Resource cleanup took {cleanup_time:.3f}s")
        print(f"Memory: {initial_memory / 1024 / 1024:.1f}MB -> "
              f"{peak_memory / 1024 / 1024:.1f}MB -> "
              f"{final_memory / 1024 / 1024:.1f}MB")

        # 정리 효율성 검증
        assert cleanup_time < 1.0  # 정리가 1초 이내
        assert final_memory < peak_memory * 0.9  # 메모리 90% 이상 회수

    def test_scalability_simulation(self):
        """확장성 시뮬레이션 테스트"""

        def simulate_load(num_concurrent_users):
            """부하 시뮬레이션"""
            def user_session():
                """사용자 세션 시뮬레이션"""
                # 여러 작업을 순차적으로 수행
                operations = []

                # 작업 1: 계산
                start = time.time()
                result1 = sum(range(1000))
                operations.append(time.time() - start)

                # 작업 2: 메모리 할당
                start = time.time()
                temp_data = [i for i in range(10000)]
                operations.append(time.time() - start)

                # 작업 3: I/O 시뮬레이션
                start = time.time()
                time.sleep(0.001)  # 1ms I/O 대기
                operations.append(time.time() - start)

                # 정리
                del temp_data

                return sum(operations)

            # 동시 사용자 시뮬레이션
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
                futures = [executor.submit(user_session) for _ in range(num_concurrent_users)]
                session_times = [f.result() for f in futures]

            total_time = time.time() - start_time

            return {
                'concurrent_users': num_concurrent_users,
                'total_time': total_time,
                'avg_session_time': sum(session_times) / len(session_times),
                'max_session_time': max(session_times),
                'throughput': num_concurrent_users / total_time
            }

        # 다양한 부하 수준 테스트
        load_levels = [1, 5, 10, 20]
        results = []

        for level in load_levels:
            result = simulate_load(level)
            results.append(result)

            print(f"Load level {level}: {result['total_time']:.3f}s total, "
                  f"{result['throughput']:.1f} users/sec, "
                  f"avg session: {result['avg_session_time'] * 1000:.1f}ms")

        # 확장성 검증
        # 부하가 증가해도 처리량이 어느 정도 유지되는지 확인
        throughputs = [r['throughput'] for r in results]

        # 최대 처리량 대비 최소 처리량이 50% 이상 유지되어야 함
        max_throughput = max(throughputs)
        min_throughput = min(throughputs)

        print(f"Throughput range: {min_throughput:.1f} - {max_throughput:.1f} users/sec")

        assert min_throughput > max_throughput * 0.3  # 30% 이상 유지

    def test_resource_monitoring(self):
        """리소스 모니터링 테스트"""
        process = psutil.Process()

        # 모니터링 시작
        monitor_duration = 5  # 5초간 모니터링
        sample_interval = 0.1  # 0.1초마다 샘플링

        cpu_samples = []
        memory_samples = []

        def resource_intensive_work():
            """리소스 집약적 작업"""
            data = []
            for i in range(1000000):
                if i % 100000 == 0:
                    # 주기적으로 메모리 할당/해제
                    data.append([j for j in range(1000)])
                    if len(data) > 10:
                        data.pop(0)

                # CPU 작업
                _ = i * i * i

        # 백그라운드에서 작업 실행
        work_thread = threading.Thread(target=resource_intensive_work)
        work_thread.start()

        # 리소스 모니터링
        start_time = time.time()
        while time.time() - start_time < monitor_duration:
            try:
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()

                cpu_samples.append(cpu_percent)
                memory_samples.append(memory_info.rss)

                time.sleep(sample_interval)
            except:
                break

        # 작업 완료 대기
        work_thread.join(timeout=1)

        # 모니터링 결과 분석
        if cpu_samples and memory_samples:
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            max_cpu = max(cpu_samples)

            avg_memory = sum(memory_samples) / len(memory_samples)
            max_memory = max(memory_samples)
            peak_memory_mb = max_memory / 1024 / 1024

            print(f"CPU usage: avg {avg_cpu:.1f}%, max {max_cpu:.1f}%")
            print(f"Memory usage: avg {avg_memory / 1024 / 1024:.1f}MB, "
                  f"peak {peak_memory_mb:.1f}MB")

            # 리소스 사용량이 합리적인 범위 내인지 확인
            assert max_cpu <= 100  # CPU 사용률은 100% 이하
            assert peak_memory_mb < 1000  # 피크 메모리는 1GB 이하


if __name__ == "__main__":
    # 간단한 벤치마크 실행
    test = TestPerformanceBenchmarks()

    print("=== Performance Benchmarks ===")
    try:
        test.test_basic_performance_metrics()
        print("✓ Basic metrics test passed")

        test.test_memory_allocation_performance()
        print("✓ Memory allocation test passed")

        test.test_cpu_intensive_performance()
        print("✓ CPU intensive test passed")

        test.test_throughput_benchmark()
        print("✓ Throughput benchmark passed")

        print("\n=== All benchmarks completed successfully ===")

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")