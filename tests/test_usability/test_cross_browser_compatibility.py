"""
크로스 브라우저 호환성 테스트 모듈

다양한 브라우저에서 웹 애플리케이션의 호환성을 테스트합니다:
- Chrome, Firefox, Safari, Edge 브라우저 지원
- JavaScript 기능 호환성 테스트
- CSS 렌더링 호환성 테스트
- 브라우저별 성능 비교
"""

import json
import os
import platform
import time
from typing import Dict, List, Optional, Tuple

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService


class BrowserTestResult:
    """브라우저 테스트 결과를 저장하는 클래스"""

    def __init__(self, browser_name: str):
        self.browser_name = browser_name
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.performance_metrics = {}
        self.supported_features = []
        self.unsupported_features = []

    def add_test_result(self, test_name: str, passed: bool, error: str = None):
        """테스트 결과 추가"""
        if passed:
            self.tests_passed += 1
        else:
            self.tests_failed += 1
            if error:
                self.errors.append(f"{test_name}: {error}")

    def add_performance_metric(self, metric_name: str, value: float):
        """성능 메트릭 추가"""
        self.performance_metrics[metric_name] = value

    def add_feature_support(self, feature_name: str, supported: bool):
        """기능 지원 여부 추가"""
        if supported:
            self.supported_features.append(feature_name)
        else:
            self.unsupported_features.append(feature_name)

    def get_success_rate(self) -> float:
        """성공률 계산"""
        total_tests = self.tests_passed + self.tests_failed
        return (self.tests_passed / total_tests * 100) if total_tests > 0 else 0

    def print_summary(self):
        """테스트 결과 요약 출력"""
        print(f"\n=== {self.browser_name} 테스트 결과 ===")
        print(f"통과: {self.tests_passed}, 실패: {self.tests_failed}")
        print(f"성공률: {self.get_success_rate():.1f}%")

        if self.performance_metrics:
            print("성능 메트릭:")
            for metric, value in self.performance_metrics.items():
                print(f"  {metric}: {value:.2f}")

        if self.supported_features:
            print(f"지원 기능: {', '.join(self.supported_features)}")

        if self.unsupported_features:
            print(f"미지원 기능: {', '.join(self.unsupported_features)}")

        if self.errors:
            print("오류 목록:")
            for error in self.errors[:5]:  # 최대 5개만 표시
                print(f"  - {error}")


class BrowserManager:
    """다양한 브라우저 드라이버 관리 클래스"""

    @staticmethod
    def create_chrome_driver() -> webdriver.Chrome:
        """Chrome 드라이버 생성"""
        options = ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        service = ChromeService()
        return webdriver.Chrome(service=service, options=options)

    @staticmethod
    def create_firefox_driver() -> webdriver.Firefox:
        """Firefox 드라이버 생성"""
        options = FirefoxOptions()
        options.add_argument('--headless')
        options.add_argument('--width=1920')
        options.add_argument('--height=1080')

        service = FirefoxService()
        return webdriver.Firefox(service=service, options=options)

    @staticmethod
    def create_edge_driver() -> webdriver.Edge:
        """Edge 드라이버 생성 (Windows만)"""
        if platform.system() != "Windows":
            return None

        options = EdgeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        service = EdgeService()
        return webdriver.Edge(service=service, options=options)

    @classmethod
    def get_available_browsers(cls) -> Dict[str, callable]:
        """사용 가능한 브라우저 목록 반환"""
        browsers = {
            'Chrome': cls.create_chrome_driver,
            'Firefox': cls.create_firefox_driver,
        }

        # Windows에서만 Edge 추가
        if platform.system() == "Windows":
            browsers['Edge'] = cls.create_edge_driver

        return browsers


@pytest.fixture(scope="module")
def test_server_url():
    """테스트 서버 URL"""
    return "http://localhost:8000"


@pytest.fixture(scope="module")
def browser_manager():
    """브라우저 매니저"""
    return BrowserManager()


class TestCrossBrowserCompatibility:
    """크로스 브라우저 호환성 테스트"""

    def test_basic_page_loading_all_browsers(self, browser_manager, test_server_url):
        """모든 브라우저에서 기본 페이지 로딩 테스트"""
        print("\n=== Cross-Browser Basic Page Loading Test ===")

        available_browsers = browser_manager.get_available_browsers()
        test_results = {}

        for browser_name, browser_factory in available_browsers.items():
            print(f"\n테스트 중: {browser_name}")
            result = BrowserTestResult(browser_name)

            driver = None
            try:
                driver = browser_factory()
                start_time = time.time()

                # 페이지 로드
                driver.get(test_server_url)

                # 기본 요소 존재 확인
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                load_time = time.time() - start_time
                result.add_performance_metric("page_load_time", load_time)

                # 페이지 제목 확인
                title = driver.title
                title_test_passed = len(title) > 0
                result.add_test_result("page_title", title_test_passed)

                # 기본 구조 요소 확인
                try:
                    upload_zone = driver.find_element(By.ID, "upload-zone")
                    result.add_test_result("upload_zone_present", True)
                except:
                    result.add_test_result("upload_zone_present", False, "Upload zone not found")

                print(f"  ✓ {browser_name} 페이지 로드 성공 ({load_time:.2f}초)")

            except Exception as e:
                result.add_test_result("page_loading", False, str(e))
                print(f"  ✗ {browser_name} 페이지 로드 실패: {e}")

            finally:
                if driver:
                    driver.quit()

            test_results[browser_name] = result

        # 결과 요약
        print("\n=== Cross-Browser Test Results Summary ===")
        for browser_name, result in test_results.items():
            result.print_summary()

        # 연결 오류가 있는지 확인 (테스트 서버가 실행되지 않은 경우)
        connection_errors = []
        for browser_name, result in test_results.items():
            for error in result.errors:
                if ("Connection refused" in str(error) or "ERR_CONNECTION_REFUSED" in str(error) or
                    "connectionFailure" in str(error) or "can't establish a connection" in str(error).lower()):
                    connection_errors.append(browser_name)
                    break

        if len(connection_errors) == len(test_results):
            pytest.skip("테스트 서버가 실행 중이지 않음")

        # 최소 하나의 브라우저에서는 성공해야 함
        success_browsers = [name for name, result in test_results.items() if result.get_success_rate() > 50]
        assert len(success_browsers) > 0, "모든 브라우저에서 기본 테스트 실패"

        print(f"\n성공한 브라우저: {', '.join(success_browsers)}")
        print("=== Cross-Browser Basic Page Loading Test Completed ===\n")

    def test_javascript_features_compatibility(self, browser_manager, test_server_url):
        """JavaScript 기능 호환성 테스트"""
        print("\n=== JavaScript Features Compatibility Test ===")

        javascript_features = {
            'es6_arrow_functions': "(() => true)()",
            'es6_const': "const test = 1; test === 1",
            'es6_template_literals': "`template ${1}` === 'template 1'",
            'fetch_api': "typeof fetch === 'function'",
            'local_storage': "typeof localStorage === 'object'",
            'json_parse': "typeof JSON.parse === 'function'",
            'promise': "typeof Promise === 'function'",
            'async_await': "async function test() { return await Promise.resolve(true); }; true",
        }

        available_browsers = browser_manager.get_available_browsers()

        for browser_name, browser_factory in available_browsers.items():
            print(f"\n테스트 중: {browser_name} JavaScript 기능")
            result = BrowserTestResult(browser_name)

            driver = None
            try:
                driver = browser_factory()
                driver.get(test_server_url)

                for feature_name, js_code in javascript_features.items():
                    try:
                        # JavaScript 코드 실행
                        js_result = driver.execute_script(f"return {js_code}")
                        supported = bool(js_result)

                        result.add_feature_support(feature_name, supported)
                        result.add_test_result(feature_name, supported)

                        if supported:
                            print(f"  ✓ {feature_name}")
                        else:
                            print(f"  ✗ {feature_name}")

                    except Exception as e:
                        result.add_feature_support(feature_name, False)
                        result.add_test_result(feature_name, False, str(e))
                        print(f"  ✗ {feature_name}: {e}")

            except Exception as e:
                print(f"  ✗ {browser_name} JavaScript 테스트 실패: {e}")

            finally:
                if driver:
                    driver.quit()

            result.print_summary()

        print("=== JavaScript Features Compatibility Test Completed ===\n")

    def test_css_rendering_compatibility(self, browser_manager, test_server_url):
        """CSS 렌더링 호환성 테스트"""
        print("\n=== CSS Rendering Compatibility Test ===")

        available_browsers = browser_manager.get_available_browsers()

        for browser_name, browser_factory in available_browsers.items():
            print(f"\n테스트 중: {browser_name} CSS 렌더링")
            result = BrowserTestResult(browser_name)

            driver = None
            try:
                driver = browser_factory()
                driver.get(test_server_url)
                time.sleep(2)  # CSS 로딩 완료 대기

                # CSS 속성 테스트
                css_tests = {
                    'flexbox': self._test_flexbox_support,
                    'grid': self._test_grid_support,
                    'transforms': self._test_transform_support,
                    'transitions': self._test_transition_support,
                }

                for test_name, test_function in css_tests.items():
                    try:
                        supported = test_function(driver)
                        result.add_feature_support(test_name, supported)
                        result.add_test_result(test_name, supported)

                        print(f"  {'✓' if supported else '✗'} {test_name}")

                    except Exception as e:
                        result.add_test_result(test_name, False, str(e))
                        print(f"  ✗ {test_name}: {e}")

                # 레이아웃 일관성 테스트
                layout_consistent = self._test_layout_consistency(driver)
                result.add_test_result("layout_consistency", layout_consistent)

            except Exception as e:
                print(f"  ✗ {browser_name} CSS 테스트 실패: {e}")

            finally:
                if driver:
                    driver.quit()

            result.print_summary()

        print("=== CSS Rendering Compatibility Test Completed ===\n")

    def test_file_upload_functionality(self, browser_manager, test_server_url):
        """파일 업로드 기능 브라우저 호환성 테스트"""
        print("\n=== File Upload Functionality Test ===")

        available_browsers = browser_manager.get_available_browsers()

        for browser_name, browser_factory in available_browsers.items():
            print(f"\n테스트 중: {browser_name} 파일 업로드")
            result = BrowserTestResult(browser_name)

            driver = None
            try:
                driver = browser_factory()
                driver.get(test_server_url)

                # 파일 입력 요소 찾기
                try:
                    file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    result.add_test_result("file_input_present", True)

                    # 파일 입력 속성 확인
                    accept_attr = file_input.get_attribute("accept")
                    multiple_attr = file_input.get_attribute("multiple")

                    result.add_test_result("accept_attribute", accept_attr is not None)

                    # 드래그 앤 드롭 영역 확인
                    try:
                        drop_zone = driver.find_element(By.ID, "upload-zone")
                        result.add_test_result("drag_drop_zone", True)
                    except:
                        result.add_test_result("drag_drop_zone", False)

                    print(f"  ✓ {browser_name} 파일 업로드 요소 확인 완료")

                except Exception as e:
                    result.add_test_result("file_input_present", False, str(e))
                    print(f"  ✗ {browser_name} 파일 업로드 요소 없음")

            except Exception as e:
                print(f"  ✗ {browser_name} 파일 업로드 테스트 실패: {e}")

            finally:
                if driver:
                    driver.quit()

            result.print_summary()

        print("=== File Upload Functionality Test Completed ===\n")

    def _test_flexbox_support(self, driver) -> bool:
        """Flexbox 지원 테스트"""
        js_code = """
        var div = document.createElement('div');
        div.style.display = 'flex';
        return div.style.display === 'flex';
        """
        return driver.execute_script(js_code)

    def _test_grid_support(self, driver) -> bool:
        """CSS Grid 지원 테스트"""
        js_code = """
        var div = document.createElement('div');
        div.style.display = 'grid';
        return div.style.display === 'grid';
        """
        return driver.execute_script(js_code)

    def _test_transform_support(self, driver) -> bool:
        """CSS Transform 지원 테스트"""
        js_code = """
        var div = document.createElement('div');
        div.style.transform = 'translateX(10px)';
        return div.style.transform !== '';
        """
        return driver.execute_script(js_code)

    def _test_transition_support(self, driver) -> bool:
        """CSS Transition 지원 테스트"""
        js_code = """
        var div = document.createElement('div');
        div.style.transition = 'all 0.3s ease';
        return div.style.transition !== '';
        """
        return driver.execute_script(js_code)

    def _test_layout_consistency(self, driver) -> bool:
        """레이아웃 일관성 테스트"""
        try:
            # 주요 요소들의 위치와 크기 확인
            body = driver.find_element(By.TAG_NAME, "body")
            body_rect = body.rect

            # 뷰포트 크기와 비교
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")

            # 콘텐츠가 뷰포트를 크게 벗어나지 않는지 확인
            return (body_rect['width'] <= viewport_width + 100 and
                    body_rect['height'] >= viewport_height * 0.5)

        except:
            return False


class TestResponsiveDesignCompatibility:
    """반응형 디자인 브라우저별 호환성 테스트"""

    def test_responsive_breakpoints_all_browsers(self, browser_manager, test_server_url):
        """모든 브라우저에서 반응형 브레이크포인트 테스트"""
        print("\n=== Responsive Design Cross-Browser Test ===")

        breakpoints = [
            (375, 667, "Mobile"),
            (768, 1024, "Tablet"),
            (1920, 1080, "Desktop")
        ]

        available_browsers = browser_manager.get_available_browsers()

        for browser_name, browser_factory in available_browsers.items():
            print(f"\n테스트 중: {browser_name} 반응형 디자인")

            driver = None
            try:
                driver = browser_factory()
                driver.get(test_server_url)

                for width, height, device_type in breakpoints:
                    print(f"  {device_type} ({width}x{height}) 테스트 중...")

                    # 화면 크기 조정
                    driver.set_window_size(width, height)
                    time.sleep(1)  # 레이아웃 조정 시간

                    # 레이아웃 검증
                    layout_ok = self._verify_responsive_layout(driver, width, height)

                    if layout_ok:
                        print(f"    ✓ {device_type} 레이아웃 정상")
                    else:
                        print(f"    ✗ {device_type} 레이아웃 문제")

            except Exception as e:
                print(f"  ✗ {browser_name} 반응형 테스트 실패: {e}")

            finally:
                if driver:
                    driver.quit()

        print("=== Responsive Design Cross-Browser Test Completed ===\n")

    def _verify_responsive_layout(self, driver, screen_width, screen_height) -> bool:
        """반응형 레이아웃 검증"""
        try:
            # 주요 요소들이 화면 내에 있는지 확인
            body = driver.find_element(By.TAG_NAME, "body")
            body_width = body.size['width']

            # 가로 스크롤이 생기지 않았는지 확인
            has_horizontal_scroll = driver.execute_script(
                "return document.body.scrollWidth > window.innerWidth;"
            )

            # 콘텐츠가 적절히 배치되었는지 확인
            content_fits = body_width <= screen_width + 20  # 20px 여유
            no_horizontal_scroll = not has_horizontal_scroll

            return content_fits and no_horizontal_scroll

        except:
            return False


if __name__ == "__main__":
    # 단독 실행 시 기본 정보 출력
    print("크로스 브라우저 호환성 테스트 모듈이 로드되었습니다.")

    # 사용 가능한 브라우저 확인
    manager = BrowserManager()
    available = manager.get_available_browsers()

    print(f"\n사용 가능한 브라우저: {list(available.keys())}")
    print("\n전체 테스트를 실행하려면:")
    print("pytest tests/test_usability/test_cross_browser_compatibility.py -v")

    # 간단한 브라우저 가용성 테스트
    for browser_name, browser_factory in available.items():
        try:
            driver = browser_factory()
            print(f"✓ {browser_name} 드라이버 사용 가능")
            driver.quit()
        except Exception as e:
            print(f"✗ {browser_name} 드라이버 사용 불가: {e}")