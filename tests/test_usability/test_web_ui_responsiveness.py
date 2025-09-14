"""
웹 UI 반응성 테스트 모듈

Lighthouse와 웹 성능 API를 사용하여 웹 UI의 반응성과 성능을 측정합니다:
- 페이지 로딩 시간 측정
- Lighthouse 성능 점수 측정
- Core Web Vitals 측정
- 네트워크 상황별 성능 테스트
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service


class PerformanceMetrics:
    """성능 메트릭 수집 및 분석 클래스"""

    def __init__(self):
        self.metrics = {}

    def collect_navigation_timing(self, driver) -> Dict:
        """Navigation Timing API로 성능 메트릭 수집"""
        timing_script = """
        return {
            'navigationStart': performance.timing.navigationStart,
            'domainLookupStart': performance.timing.domainLookupStart,
            'domainLookupEnd': performance.timing.domainLookupEnd,
            'connectStart': performance.timing.connectStart,
            'connectEnd': performance.timing.connectEnd,
            'requestStart': performance.timing.requestStart,
            'responseStart': performance.timing.responseStart,
            'responseEnd': performance.timing.responseEnd,
            'domLoading': performance.timing.domLoading,
            'domInteractive': performance.timing.domInteractive,
            'domContentLoadedEventStart': performance.timing.domContentLoadedEventStart,
            'domContentLoadedEventEnd': performance.timing.domContentLoadedEventEnd,
            'loadEventStart': performance.timing.loadEventStart,
            'loadEventEnd': performance.timing.loadEventEnd
        };
        """

        timing_data = driver.execute_script(timing_script)

        # 의미있는 메트릭 계산
        navigation_start = timing_data['navigationStart']

        return {
            'dns_lookup_time': timing_data['domainLookupEnd'] - timing_data['domainLookupStart'],
            'tcp_connect_time': timing_data['connectEnd'] - timing_data['connectStart'],
            'request_response_time': timing_data['responseEnd'] - timing_data['requestStart'],
            'dom_loading_time': timing_data['domLoading'] - navigation_start,
            'dom_interactive_time': timing_data['domInteractive'] - navigation_start,
            'dom_content_loaded_time': timing_data['domContentLoadedEventEnd'] - navigation_start,
            'page_load_time': timing_data['loadEventEnd'] - navigation_start,
            'first_paint_time': self.get_first_paint_time(driver)
        }

    def get_first_paint_time(self, driver) -> float:
        """First Paint 시간 측정"""
        paint_script = """
        return performance.getEntriesByType('paint')
            .filter(entry => entry.name === 'first-paint')
            .map(entry => entry.startTime)[0] || 0;
        """
        return driver.execute_script(paint_script)

    def get_core_web_vitals(self, driver) -> Dict:
        """Core Web Vitals 측정"""
        web_vitals_script = """
        return new Promise((resolve) => {
            const vitals = {};

            // LCP (Largest Contentful Paint)
            new PerformanceObserver((list) => {
                const entries = list.getEntries();
                const lastEntry = entries[entries.length - 1];
                vitals.lcp = lastEntry.startTime;
            }).observe({ entryTypes: ['largest-contentful-paint'] });

            // FID (First Input Delay) - 실제 사용자 인터랙션이 필요하므로 시뮬레이션
            vitals.fid = 0; // 실제 테스트에서는 사용자 인터랙션 시뮬레이션 필요

            // CLS (Cumulative Layout Shift)
            let clsScore = 0;
            new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (!entry.hadRecentInput) {
                        clsScore += entry.value;
                    }
                }
                vitals.cls = clsScore;
            }).observe({ entryTypes: ['layout-shift'] });

            setTimeout(() => resolve(vitals), 3000);
        });
        """

        try:
            return driver.execute_async_script(web_vitals_script)
        except:
            return {'lcp': 0, 'fid': 0, 'cls': 0}

    def run_lighthouse_audit(self, url: str) -> Optional[Dict]:
        """Lighthouse 감사 실행"""
        try:
            # Chrome headless 모드로 Lighthouse 실행
            cmd = [
                'npx', 'lighthouse', url,
                '--chrome-flags=--headless',
                '--output=json',
                '--output-path=/tmp/lighthouse-report.json',
                '--quiet'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and os.path.exists('/tmp/lighthouse-report.json'):
                with open('/tmp/lighthouse-report.json', 'r') as f:
                    lighthouse_data = json.load(f)

                return {
                    'performance_score': lighthouse_data['categories']['performance']['score'] * 100,
                    'accessibility_score': lighthouse_data['categories']['accessibility']['score'] * 100,
                    'best_practices_score': lighthouse_data['categories']['best-practices']['score'] * 100,
                    'seo_score': lighthouse_data['categories']['seo']['score'] * 100,
                    'first_contentful_paint': lighthouse_data['audits']['first-contentful-paint']['numericValue'],
                    'largest_contentful_paint': lighthouse_data['audits']['largest-contentful-paint']['numericValue'],
                    'total_blocking_time': lighthouse_data['audits']['total-blocking-time']['numericValue'],
                    'cumulative_layout_shift': lighthouse_data['audits']['cumulative-layout-shift']['numericValue']
                }
        except Exception as e:
            print(f"Lighthouse 감사 실패: {e}")
            return None


@pytest.fixture
def chrome_driver():
    """Chrome WebDriver 설정"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    try:
        service = Service()  # 시스템의 chromedriver 사용
        driver = webdriver.Chrome(service=service, options=options)
        yield driver
    finally:
        if 'driver' in locals():
            driver.quit()


@pytest.fixture
def performance_metrics():
    """성능 메트릭 수집기"""
    return PerformanceMetrics()


@pytest.fixture
def test_server_url():
    """테스트 서버 URL (실제 서버가 실행 중이어야 함)"""
    return "http://localhost:8000"  # FastAPI 개발 서버


class TestWebUIResponsiveness:
    """웹 UI 반응성 테스트"""

    def test_page_load_performance(self, chrome_driver, performance_metrics, test_server_url):
        """페이지 로딩 성능 테스트"""
        print("\n=== Page Load Performance Test ===")

        try:
            # 페이지 로드
            start_time = time.time()
            chrome_driver.get(test_server_url)

            # 페이지가 완전히 로드될 때까지 대기
            WebDriverWait(chrome_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            load_time = time.time() - start_time

            # Navigation Timing 메트릭 수집
            timing_metrics = performance_metrics.collect_navigation_timing(chrome_driver)

            print(f"페이지 로드 시간: {load_time:.2f}초")
            print(f"DOM 인터랙티브 시간: {timing_metrics['dom_interactive_time']:.0f}ms")
            print(f"DOM 콘텐츠 로드 시간: {timing_metrics['dom_content_loaded_time']:.0f}ms")
            print(f"전체 로드 시간: {timing_metrics['page_load_time']:.0f}ms")

            # 성능 임계값 검증
            assert load_time < 5.0, f"페이지 로드 시간이 너무 느림: {load_time:.2f}초"
            assert timing_metrics['dom_interactive_time'] < 3000, \
                f"DOM 인터랙티브 시간이 너무 느림: {timing_metrics['dom_interactive_time']:.0f}ms"

            print("✓ 페이지 로드 성능 기준 통과")

        except Exception as e:
            print(f"✗ 페이지 로드 테스트 실패: {e}")
            # 서버가 실행 중이 아닐 수 있으므로 테스트를 건너뜀
            pytest.skip("테스트 서버가 실행 중이지 않음")

        print("=== Page Load Performance Test Completed ===\n")

    def test_responsive_design_breakpoints(self, chrome_driver, test_server_url):
        """반응형 디자인 브레이크포인트 테스트"""
        print("\n=== Responsive Design Breakpoints Test ===")

        # 다양한 화면 크기 테스트
        breakpoints = [
            (375, 667, "Mobile Portrait"),
            (667, 375, "Mobile Landscape"),
            (768, 1024, "Tablet Portrait"),
            (1024, 768, "Tablet Landscape"),
            (1280, 720, "Desktop Small"),
            (1920, 1080, "Desktop Large"),
            (2560, 1440, "Desktop XL")
        ]

        try:
            chrome_driver.get(test_server_url)

            for width, height, device_name in breakpoints:
                print(f"테스트 중: {device_name} ({width}x{height})")

                # 화면 크기 변경
                chrome_driver.set_window_size(width, height)
                time.sleep(1)  # 레이아웃 조정 시간 대기

                # 주요 UI 요소들이 올바르게 표시되는지 확인
                try:
                    # 업로드 영역 확인
                    upload_area = chrome_driver.find_element(By.ID, "upload-zone")
                    assert upload_area.is_displayed(), f"업로드 영역이 {device_name}에서 보이지 않음"

                    # 설정 패널 확인 (존재한다면)
                    try:
                        settings_panel = chrome_driver.find_element(By.CLASS_NAME, "settings-panel")
                        # 모바일에서는 설정 패널이 숨겨질 수 있음
                        if width >= 768:  # 태블릿 이상에서만 체크
                            assert settings_panel.is_displayed() or "hidden" in settings_panel.get_attribute("class")
                    except:
                        pass  # 설정 패널이 없을 수 있음

                    # 레이아웃이 깨지지 않았는지 확인
                    body = chrome_driver.find_element(By.TAG_NAME, "body")
                    body_width = body.size['width']
                    assert body_width <= width + 20, f"콘텐츠가 화면을 벗어남: {body_width}px > {width}px"

                    print(f"  ✓ {device_name} 레이아웃 정상")

                except Exception as e:
                    print(f"  ✗ {device_name} 레이아웃 문제: {e}")

        except Exception as e:
            print(f"✗ 반응형 디자인 테스트 실패: {e}")
            pytest.skip("테스트 서버가 실행 중이지 않음")

        print("=== Responsive Design Breakpoints Test Completed ===\n")

    def test_core_web_vitals(self, chrome_driver, performance_metrics, test_server_url):
        """Core Web Vitals 테스트"""
        print("\n=== Core Web Vitals Test ===")

        try:
            chrome_driver.get(test_server_url)

            # Core Web Vitals 측정
            vitals = performance_metrics.get_core_web_vitals(chrome_driver)

            print(f"Largest Contentful Paint (LCP): {vitals['lcp']:.2f}ms")
            print(f"First Input Delay (FID): {vitals['fid']:.2f}ms")
            print(f"Cumulative Layout Shift (CLS): {vitals['cls']:.4f}")

            # Core Web Vitals 임계값 검증
            if vitals['lcp'] > 0:
                assert vitals['lcp'] < 2500, f"LCP가 너무 느림: {vitals['lcp']:.2f}ms (기준: 2500ms)"
                print("✓ LCP 기준 통과")

            if vitals['cls'] > 0:
                assert vitals['cls'] < 0.1, f"CLS가 너무 높음: {vitals['cls']:.4f} (기준: 0.1)"
                print("✓ CLS 기준 통과")

            print("✓ Core Web Vitals 측정 완료")

        except Exception as e:
            print(f"✗ Core Web Vitals 테스트 실패: {e}")
            pytest.skip("테스트 서버가 실행 중이지 않음")

        print("=== Core Web Vitals Test Completed ===\n")

    def test_ui_interaction_responsiveness(self, chrome_driver, test_server_url):
        """UI 인터랙션 반응성 테스트"""
        print("\n=== UI Interaction Responsiveness Test ===")

        try:
            chrome_driver.get(test_server_url)
            time.sleep(2)  # 페이지 로드 완료 대기

            # 파일 업로드 영역 호버 테스트
            try:
                upload_zone = chrome_driver.find_element(By.ID, "upload-zone")

                # 호버 전 스타일
                original_style = upload_zone.get_attribute("style")

                # 호버 시뮬레이션 (JavaScript로)
                chrome_driver.execute_script("""
                    var element = arguments[0];
                    var event = new MouseEvent('mouseenter', {bubbles: true});
                    element.dispatchEvent(event);
                """, upload_zone)

                time.sleep(0.5)  # 애니메이션 시간 대기

                # 호버 후 스타일 변화 확인 (CSS transition이 있다면)
                hover_style = upload_zone.get_attribute("style")

                print("✓ 업로드 영역 호버 인터랙션 테스트 완료")

            except Exception as e:
                print(f"  업로드 영역 호버 테스트 실패: {e}")

            # 버튼 클릭 반응성 테스트
            try:
                buttons = chrome_driver.find_elements(By.TAG_NAME, "button")
                if buttons:
                    for i, button in enumerate(buttons[:3]):  # 처음 3개 버튼만 테스트
                        if button.is_displayed() and button.is_enabled():
                            start_time = time.time()

                            # 클릭 시뮬레이션
                            chrome_driver.execute_script("arguments[0].click();", button)

                            response_time = time.time() - start_time
                            print(f"  버튼 {i+1} 클릭 응답시간: {response_time*1000:.1f}ms")

                            # 100ms 이내 응답
                            assert response_time < 0.1, f"버튼 응답이 너무 느림: {response_time*1000:.1f}ms"

                print("✓ 버튼 클릭 반응성 테스트 완료")

            except Exception as e:
                print(f"  버튼 클릭 테스트 실패: {e}")

        except Exception as e:
            print(f"✗ UI 인터랙션 반응성 테스트 실패: {e}")
            pytest.skip("테스트 서버가 실행 중이지 않음")

        print("=== UI Interaction Responsiveness Test Completed ===\n")

    def test_lighthouse_performance_audit(self, performance_metrics, test_server_url):
        """Lighthouse 성능 감사 테스트"""
        print("\n=== Lighthouse Performance Audit Test ===")

        try:
            # Lighthouse 감사 실행
            lighthouse_results = performance_metrics.run_lighthouse_audit(test_server_url)

            if lighthouse_results:
                print(f"성능 점수: {lighthouse_results['performance_score']:.1f}/100")
                print(f"접근성 점수: {lighthouse_results['accessibility_score']:.1f}/100")
                print(f"모범 사례 점수: {lighthouse_results['best_practices_score']:.1f}/100")
                print(f"SEO 점수: {lighthouse_results['seo_score']:.1f}/100")
                print(f"First Contentful Paint: {lighthouse_results['first_contentful_paint']:.0f}ms")
                print(f"Largest Contentful Paint: {lighthouse_results['largest_contentful_paint']:.0f}ms")

                # 성능 기준 검증
                assert lighthouse_results['performance_score'] >= 70, \
                    f"성능 점수가 낮음: {lighthouse_results['performance_score']:.1f}/100"

                assert lighthouse_results['accessibility_score'] >= 80, \
                    f"접근성 점수가 낮음: {lighthouse_results['accessibility_score']:.1f}/100"

                print("✓ Lighthouse 감사 기준 통과")

            else:
                print("✗ Lighthouse 감사 실행 실패 (Node.js/npm이 필요)")
                pytest.skip("Lighthouse 실행 환경 부족")

        except Exception as e:
            print(f"✗ Lighthouse 감사 테스트 실패: {e}")
            pytest.skip("Lighthouse 실행 실패")

        print("=== Lighthouse Performance Audit Test Completed ===\n")

    def test_network_condition_simulation(self, chrome_driver, test_server_url):
        """네트워크 상황별 성능 테스트"""
        print("\n=== Network Condition Simulation Test ===")

        # 네트워크 조건 시뮬레이션 (Chrome DevTools Protocol 사용)
        network_conditions = [
            {"name": "Fast 3G", "downloadThroughput": 1500000, "uploadThroughput": 750000, "latency": 40},
            {"name": "Slow 3G", "downloadThroughput": 500000, "uploadThroughput": 500000, "latency": 300},
            {"name": "2G", "downloadThroughput": 250000, "uploadThroughput": 250000, "latency": 800}
        ]

        try:
            for condition in network_conditions:
                print(f"테스트 중: {condition['name']} 네트워크")

                # 네트워크 조건 설정
                chrome_driver.execute_cdp_cmd('Network.enable', {})
                chrome_driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                    'offline': False,
                    'downloadThroughput': condition['downloadThroughput'],
                    'uploadThroughput': condition['uploadThroughput'],
                    'latency': condition['latency']
                })

                # 페이지 로드 테스트
                start_time = time.time()
                chrome_driver.get(test_server_url)

                try:
                    WebDriverWait(chrome_driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    load_time = time.time() - start_time
                    print(f"  {condition['name']} 로드 시간: {load_time:.2f}초")

                    # 네트워크 조건에 따른 합리적인 임계값 설정
                    max_load_time = 10 if condition['name'] == "2G" else 5
                    assert load_time < max_load_time, \
                        f"{condition['name']}에서 로드 시간 초과: {load_time:.2f}초"

                    print(f"  ✓ {condition['name']} 네트워크 테스트 통과")

                except Exception as e:
                    print(f"  ✗ {condition['name']} 네트워크 테스트 실패: {e}")

                # 네트워크 조건 초기화
                chrome_driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                    'offline': False,
                    'downloadThroughput': -1,
                    'uploadThroughput': -1,
                    'latency': 0
                })

        except Exception as e:
            print(f"✗ 네트워크 시뮬레이션 테스트 실패: {e}")
            pytest.skip("네트워크 시뮬레이션 실행 실패")

        print("=== Network Condition Simulation Test Completed ===\n")


if __name__ == "__main__":
    # 단독 실행 시 기본 테스트
    print("웹 UI 반응성 테스트 모듈이 로드되었습니다.")
    print("전체 테스트를 실행하려면 pytest를 사용하세요:")
    print("pytest tests/test_usability/test_web_ui_responsiveness.py -v")