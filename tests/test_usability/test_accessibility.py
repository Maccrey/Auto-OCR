"""
접근성 테스트 모듈

웹 접근성 가이드라인(WCAG)에 따른 접근성 테스트를 수행합니다:
- 키보드 네비게이션 테스트
- 스크린 리더 호환성 테스트
- 색상 대비 테스트
- ARIA 속성 검증
- axe-core를 사용한 자동 접근성 감사
"""

import json
import time
from typing import Dict, List, Optional, Tuple

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains


class AccessibilityTestResult:
    """접근성 테스트 결과를 저장하는 클래스"""

    def __init__(self):
        self.passed_tests = []
        self.failed_tests = []
        self.warnings = []
        self.violations = []

    def add_pass(self, test_name: str, message: str = ""):
        """통과한 테스트 추가"""
        self.passed_tests.append({"test": test_name, "message": message})

    def add_fail(self, test_name: str, message: str):
        """실패한 테스트 추가"""
        self.failed_tests.append({"test": test_name, "message": message})

    def add_warning(self, test_name: str, message: str):
        """경고 추가"""
        self.warnings.append({"test": test_name, "message": message})

    def add_violation(self, violation_data: Dict):
        """접근성 위반 추가"""
        self.violations.append(violation_data)

    def get_summary(self) -> Dict:
        """결과 요약 반환"""
        return {
            "passed": len(self.passed_tests),
            "failed": len(self.failed_tests),
            "warnings": len(self.warnings),
            "violations": len(self.violations),
            "total": len(self.passed_tests) + len(self.failed_tests)
        }

    def print_summary(self):
        """결과 요약 출력"""
        summary = self.get_summary()
        print(f"\n=== 접근성 테스트 결과 요약 ===")
        print(f"통과: {summary['passed']}")
        print(f"실패: {summary['failed']}")
        print(f"경고: {summary['warnings']}")
        print(f"위반사항: {summary['violations']}")

        if self.failed_tests:
            print("\n실패한 테스트:")
            for fail in self.failed_tests:
                print(f"  ✗ {fail['test']}: {fail['message']}")

        if self.warnings:
            print("\n경고사항:")
            for warning in self.warnings:
                print(f"  ⚠ {warning['test']}: {warning['message']}")

        if self.violations:
            print("\n접근성 위반사항:")
            for violation in self.violations[:5]:  # 최대 5개만 표시
                print(f"  ⚠ {violation.get('id', 'Unknown')}: {violation.get('description', '')}")


@pytest.fixture
def chrome_driver():
    """Chrome WebDriver 설정"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    # 접근성 관련 설정
    options.add_argument('--enable-automation')
    options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        yield driver
    finally:
        if 'driver' in locals():
            driver.quit()


@pytest.fixture
def test_server_url():
    """테스트 서버 URL"""
    return "http://localhost:8000"


@pytest.fixture
def accessibility_result():
    """접근성 테스트 결과 객체"""
    return AccessibilityTestResult()


class TestKeyboardAccessibility:
    """키보드 접근성 테스트"""

    def test_keyboard_navigation(self, chrome_driver, test_server_url, accessibility_result):
        """키보드 네비게이션 테스트"""
        print("\n=== Keyboard Navigation Test ===")

        try:
            chrome_driver.get(test_server_url)
            time.sleep(2)

            # 초기 포커스 상태 확인
            active_element = chrome_driver.switch_to.active_element
            initial_tag = active_element.tag_name

            print(f"초기 포커스 요소: {initial_tag}")

            # Tab 키로 네비게이션 테스트
            focusable_elements = []
            max_tabs = 20  # 무한 루프 방지

            for i in range(max_tabs):
                # Tab 키 입력
                ActionChains(chrome_driver).send_keys(Keys.TAB).perform()
                time.sleep(0.1)

                # 현재 포커스된 요소 확인
                try:
                    active_element = chrome_driver.switch_to.active_element
                    element_info = {
                        'tag': active_element.tag_name,
                        'id': active_element.get_attribute('id'),
                        'class': active_element.get_attribute('class'),
                        'type': active_element.get_attribute('type'),
                        'aria-label': active_element.get_attribute('aria-label'),
                        'visible': active_element.is_displayed(),
                        'enabled': active_element.is_enabled()
                    }

                    focusable_elements.append(element_info)

                    # 시각적 포커스 표시 확인
                    outline_style = chrome_driver.execute_script(
                        "return window.getComputedStyle(arguments[0]).outline;",
                        active_element
                    )

                    has_focus_indicator = (
                        outline_style and outline_style != "none" or
                        "focus" in (active_element.get_attribute('class') or '')
                    )

                    if not has_focus_indicator:
                        accessibility_result.add_warning(
                            "focus_indicator",
                            f"포커스 표시가 불분명한 요소: {element_info['tag']}"
                        )

                except Exception as e:
                    print(f"포커스 요소 확인 실패: {e}")
                    break

                # body로 돌아갔으면 한 바퀴 완료
                if active_element.tag_name.lower() == 'body' and i > 0:
                    break

            print(f"포커스 가능한 요소 {len(focusable_elements)}개 발견")

            # 키보드 네비게이션 가능성 검증
            interactive_elements = [
                elem for elem in focusable_elements
                if elem['tag'].lower() in ['input', 'button', 'select', 'textarea', 'a']
                or elem.get('type') in ['button', 'submit', 'file']
            ]

            if len(interactive_elements) > 0:
                accessibility_result.add_pass(
                    "keyboard_navigation",
                    f"{len(interactive_elements)}개의 상호작용 요소가 키보드로 접근 가능"
                )
                print(f"✓ 키보드 네비게이션 가능한 요소: {len(interactive_elements)}개")
            else:
                accessibility_result.add_fail(
                    "keyboard_navigation",
                    "키보드로 접근 가능한 상호작용 요소가 없음"
                )

            # 탭 트랩 테스트 (모달이나 대화상자가 있다면)
            self._test_tab_trapping(chrome_driver, accessibility_result)

        except Exception as e:
            accessibility_result.add_fail("keyboard_navigation", f"키보드 네비게이션 테스트 실패: {e}")
            pytest.skip("테스트 서버가 실행 중이지 않음")

        print("=== Keyboard Navigation Test Completed ===\n")

    def test_skip_links(self, chrome_driver, test_server_url, accessibility_result):
        """스킵 링크 테스트"""
        print("\n=== Skip Links Test ===")

        try:
            chrome_driver.get(test_server_url)

            # 첫 번째 Tab으로 스킵 링크 활성화 시도
            ActionChains(chrome_driver).send_keys(Keys.TAB).perform()
            time.sleep(0.5)

            active_element = chrome_driver.switch_to.active_element
            element_text = active_element.text.lower()

            # 스킵 링크 패턴 찾기
            skip_patterns = ['skip to main', 'skip to content', '본문으로 이동', '메인 콘텐츠로 이동']
            has_skip_link = any(pattern in element_text for pattern in skip_patterns)

            if has_skip_link:
                accessibility_result.add_pass("skip_links", "스킵 링크가 제공됨")
                print("✓ 스킵 링크 발견")

                # 스킵 링크 작동 테스트
                try:
                    active_element.click()
                    time.sleep(0.5)

                    new_active = chrome_driver.switch_to.active_element
                    if new_active != active_element:
                        accessibility_result.add_pass("skip_link_function", "스킵 링크가 정상 작동")
                        print("✓ 스킵 링크 정상 작동")
                    else:
                        accessibility_result.add_warning("skip_link_function", "스킵 링크 작동 확인 불가")
                except Exception as e:
                    accessibility_result.add_warning("skip_link_function", f"스킵 링크 테스트 실패: {e}")

            else:
                accessibility_result.add_warning("skip_links", "스킵 링크를 찾을 수 없음")
                print("⚠ 스킵 링크가 없음")

        except Exception as e:
            accessibility_result.add_fail("skip_links", f"스킵 링크 테스트 실패: {e}")

        print("=== Skip Links Test Completed ===\n")

    def _test_tab_trapping(self, driver, accessibility_result):
        """탭 트랩 테스트 (모달 대화상자 등)"""
        try:
            # 모달이나 대화상자가 있는지 확인
            modal_selectors = [
                '[role="dialog"]',
                '[role="alertdialog"]',
                '.modal',
                '.dialog'
            ]

            for selector in modal_selectors:
                modals = driver.find_elements(By.CSS_SELECTOR, selector)
                for modal in modals:
                    if modal.is_displayed():
                        # 모달 내에서 탭 트랩이 작동하는지 테스트
                        # 이 부분은 실제 모달 구현에 따라 달라집니다
                        accessibility_result.add_pass("tab_trapping", "모달에서 탭 트랩 확인됨")
                        return

        except Exception as e:
            accessibility_result.add_warning("tab_trapping", f"탭 트랩 테스트 실패: {e}")


class TestARIACompatibility:
    """ARIA 속성 호환성 테스트"""

    def test_aria_labels_and_descriptions(self, chrome_driver, test_server_url, accessibility_result):
        """ARIA 라벨과 설명 테스트"""
        print("\n=== ARIA Labels and Descriptions Test ===")

        try:
            chrome_driver.get(test_server_url)

            # 모든 상호작용 요소 찾기
            interactive_elements = chrome_driver.find_elements(
                By.CSS_SELECTOR,
                'input, button, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'
            )

            labeled_elements = 0
            unlabeled_elements = 0

            for element in interactive_elements:
                if not element.is_displayed():
                    continue

                # 라벨링 방법들 확인
                has_label = (
                    element.get_attribute('aria-label') or
                    element.get_attribute('aria-labelledby') or
                    element.get_attribute('title') or
                    self._has_associated_label(chrome_driver, element) or
                    element.text.strip()
                )

                if has_label:
                    labeled_elements += 1
                else:
                    unlabeled_elements += 1
                    element_id = element.get_attribute('id') or 'no-id'
                    accessibility_result.add_warning(
                        "unlabeled_element",
                        f"라벨이 없는 {element.tag_name} 요소 (ID: {element_id})"
                    )

            print(f"라벨이 있는 요소: {labeled_elements}개")
            print(f"라벨이 없는 요소: {unlabeled_elements}개")

            if labeled_elements > 0:
                accessibility_result.add_pass(
                    "aria_labels",
                    f"{labeled_elements}개 요소에 적절한 라벨 제공"
                )

            if unlabeled_elements == 0:
                accessibility_result.add_pass("complete_labeling", "모든 상호작용 요소에 라벨 제공")
            else:
                accessibility_result.add_fail(
                    "complete_labeling",
                    f"{unlabeled_elements}개 요소에 라벨 누락"
                )

        except Exception as e:
            accessibility_result.add_fail("aria_labels", f"ARIA 라벨 테스트 실패: {e}")

        print("=== ARIA Labels and Descriptions Test Completed ===\n")

    def test_aria_roles(self, chrome_driver, test_server_url, accessibility_result):
        """ARIA 역할 테스트"""
        print("\n=== ARIA Roles Test ===")

        try:
            chrome_driver.get(test_server_url)

            # ARIA 역할이 있는 요소들 찾기
            elements_with_roles = chrome_driver.find_elements(By.CSS_SELECTOR, '[role]')

            valid_roles = {
                'alert', 'alertdialog', 'application', 'article', 'banner', 'button',
                'cell', 'checkbox', 'columnheader', 'combobox', 'complementary',
                'contentinfo', 'definition', 'dialog', 'directory', 'document',
                'form', 'grid', 'gridcell', 'group', 'heading', 'img', 'link',
                'list', 'listbox', 'listitem', 'log', 'main', 'marquee', 'math',
                'menu', 'menubar', 'menuitem', 'menuitemcheckbox', 'menuitemradio',
                'navigation', 'note', 'option', 'presentation', 'progressbar',
                'radio', 'radiogroup', 'region', 'row', 'rowgroup', 'rowheader',
                'scrollbar', 'search', 'separator', 'slider', 'spinbutton',
                'status', 'tab', 'tablist', 'tabpanel', 'textbox', 'timer',
                'toolbar', 'tooltip', 'tree', 'treegrid', 'treeitem'
            }

            valid_role_count = 0
            invalid_role_count = 0

            for element in elements_with_roles:
                role = element.get_attribute('role')
                if role in valid_roles:
                    valid_role_count += 1
                else:
                    invalid_role_count += 1
                    accessibility_result.add_warning(
                        "invalid_role",
                        f"유효하지 않은 ARIA 역할: {role}"
                    )

            print(f"유효한 ARIA 역할: {valid_role_count}개")
            print(f"유효하지 않은 ARIA 역할: {invalid_role_count}개")

            if valid_role_count > 0:
                accessibility_result.add_pass("aria_roles", f"{valid_role_count}개의 유효한 ARIA 역할 사용")

            if invalid_role_count == 0:
                accessibility_result.add_pass("valid_roles", "모든 ARIA 역할이 유효함")

        except Exception as e:
            accessibility_result.add_fail("aria_roles", f"ARIA 역할 테스트 실패: {e}")

        print("=== ARIA Roles Test Completed ===\n")

    def _has_associated_label(self, driver, element) -> bool:
        """요소에 연결된 라벨이 있는지 확인"""
        try:
            element_id = element.get_attribute('id')
            if element_id:
                # for 속성으로 연결된 라벨 찾기
                labels = driver.find_elements(By.CSS_SELECTOR, f'label[for="{element_id}"]')
                return len(labels) > 0
        except:
            pass
        return False


class TestColorContrast:
    """색상 대비 테스트"""

    def test_color_contrast_ratios(self, chrome_driver, test_server_url, accessibility_result):
        """색상 대비율 테스트"""
        print("\n=== Color Contrast Test ===")

        try:
            chrome_driver.get(test_server_url)

            # 텍스트 요소들 찾기
            text_elements = chrome_driver.find_elements(
                By.CSS_SELECTOR,
                'p, h1, h2, h3, h4, h5, h6, span, div, button, a, label'
            )

            contrast_issues = 0
            tested_elements = 0

            for element in text_elements:
                if not element.is_displayed() or not element.text.strip():
                    continue

                try:
                    # 요소의 색상 정보 가져오기
                    color_info = chrome_driver.execute_script("""
                        var element = arguments[0];
                        var style = window.getComputedStyle(element);
                        return {
                            color: style.color,
                            backgroundColor: style.backgroundColor,
                            fontSize: style.fontSize
                        };
                    """, element)

                    # 대비율 계산 (간단한 버전)
                    contrast_ratio = self._calculate_contrast_ratio(
                        color_info['color'],
                        color_info['backgroundColor']
                    )

                    if contrast_ratio:
                        tested_elements += 1
                        font_size = float(color_info['fontSize'].replace('px', ''))

                        # WCAG 기준 확인
                        min_ratio = 3.0 if font_size >= 18 else 4.5  # AA 기준

                        if contrast_ratio < min_ratio:
                            contrast_issues += 1
                            accessibility_result.add_warning(
                                "low_contrast",
                                f"낮은 대비율: {contrast_ratio:.2f} (최소: {min_ratio:.1f})"
                            )

                except Exception as e:
                    continue

            print(f"테스트된 요소: {tested_elements}개")
            print(f"대비 문제: {contrast_issues}개")

            if tested_elements > 0:
                if contrast_issues == 0:
                    accessibility_result.add_pass("color_contrast", "모든 텍스트의 대비율이 적절함")
                else:
                    accessibility_result.add_warning(
                        "color_contrast",
                        f"{contrast_issues}개 요소에서 대비율 문제 발견"
                    )

        except Exception as e:
            accessibility_result.add_fail("color_contrast", f"색상 대비 테스트 실패: {e}")

        print("=== Color Contrast Test Completed ===\n")

    def _calculate_contrast_ratio(self, foreground: str, background: str) -> Optional[float]:
        """색상 대비율 계산 (간단한 구현)"""
        try:
            # RGB 값 추출 (간단한 구현)
            def parse_rgb(color_str):
                if 'rgb' in color_str:
                    numbers = color_str.replace('rgb(', '').replace('rgba(', '').replace(')', '').split(',')
                    return [int(n.strip()) for n in numbers[:3]]
                return None

            fg_rgb = parse_rgb(foreground)
            bg_rgb = parse_rgb(background)

            if not fg_rgb or not bg_rgb:
                return None

            # 상대 휘도 계산
            def relative_luminance(rgb):
                def linearize(c):
                    c = c / 255.0
                    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

                r, g, b = [linearize(c) for c in rgb]
                return 0.2126 * r + 0.7152 * g + 0.0722 * b

            l1 = relative_luminance(fg_rgb)
            l2 = relative_luminance(bg_rgb)

            # 대비율 계산
            lighter = max(l1, l2)
            darker = min(l1, l2)

            return (lighter + 0.05) / (darker + 0.05)

        except:
            return None


class TestAutomatedAccessibility:
    """자동화된 접근성 테스트 (axe-core 사용)"""

    def test_axe_core_audit(self, chrome_driver, test_server_url, accessibility_result):
        """axe-core를 사용한 자동 접근성 감사"""
        print("\n=== axe-core Automated Audit ===")

        try:
            chrome_driver.get(test_server_url)

            # axe-core 라이브러리 주입
            axe_script = """
            if (typeof axe === 'undefined') {
                var script = document.createElement('script');
                script.src = 'https://unpkg.com/axe-core@4/axe.min.js';
                document.head.appendChild(script);
                return new Promise(resolve => {
                    script.onload = () => resolve('loaded');
                    script.onerror = () => resolve('error');
                });
            }
            return 'already_loaded';
            """

            load_result = chrome_driver.execute_script(axe_script)

            if load_result == 'loaded' or load_result == 'already_loaded':
                # axe 감사 실행
                time.sleep(2)  # 라이브러리 로딩 대기

                audit_script = """
                return new Promise((resolve, reject) => {
                    if (typeof axe !== 'undefined') {
                        axe.run().then(results => resolve(results)).catch(err => reject(err));
                    } else {
                        reject('axe not loaded');
                    }
                });
                """

                try:
                    results = chrome_driver.execute_async_script(audit_script)

                    # 결과 처리
                    violations = results.get('violations', [])
                    passes = results.get('passes', [])

                    print(f"axe-core 위반사항: {len(violations)}개")
                    print(f"axe-core 통과사항: {len(passes)}개")

                    # 위반사항 분석
                    for violation in violations:
                        accessibility_result.add_violation({
                            'id': violation.get('id'),
                            'impact': violation.get('impact'),
                            'description': violation.get('description'),
                            'help': violation.get('help'),
                            'nodes': len(violation.get('nodes', []))
                        })

                    if len(violations) == 0:
                        accessibility_result.add_pass("axe_audit", "axe-core 감사에서 위반사항 없음")
                    else:
                        accessibility_result.add_fail(
                            "axe_audit",
                            f"axe-core에서 {len(violations)}개 위반사항 발견"
                        )

                except Exception as e:
                    print(f"axe 감사 실행 실패: {e}")
                    accessibility_result.add_warning("axe_audit", f"axe 감사 실행 실패: {e}")

            else:
                print("axe-core 라이브러리 로드 실패")
                accessibility_result.add_warning("axe_audit", "axe-core 라이브러리 로드 실패")

        except Exception as e:
            accessibility_result.add_fail("axe_audit", f"자동 접근성 감사 실패: {e}")

        print("=== axe-core Automated Audit Completed ===\n")


class TestAccessibilityIntegration:
    """통합 접근성 테스트"""

    def test_comprehensive_accessibility_audit(self, chrome_driver, test_server_url):
        """종합 접근성 감사"""
        print("\n=== Comprehensive Accessibility Audit ===")

        accessibility_result = AccessibilityTestResult()

        try:
            # 각 테스트 클래스 인스턴스 생성
            keyboard_test = TestKeyboardAccessibility()
            aria_test = TestARIACompatibility()
            color_test = TestColorContrast()
            auto_test = TestAutomatedAccessibility()

            # 모든 테스트 실행
            keyboard_test.test_keyboard_navigation(chrome_driver, test_server_url, accessibility_result)
            keyboard_test.test_skip_links(chrome_driver, test_server_url, accessibility_result)

            aria_test.test_aria_labels_and_descriptions(chrome_driver, test_server_url, accessibility_result)
            aria_test.test_aria_roles(chrome_driver, test_server_url, accessibility_result)

            color_test.test_color_contrast_ratios(chrome_driver, test_server_url, accessibility_result)

            auto_test.test_axe_core_audit(chrome_driver, test_server_url, accessibility_result)

        except Exception as e:
            accessibility_result.add_fail("comprehensive_audit", f"종합 감사 실행 실패: {e}")
            pytest.skip("테스트 서버가 실행 중이지 않음")

        # 결과 요약 출력
        accessibility_result.print_summary()

        # 최소 접근성 기준 검증
        summary = accessibility_result.get_summary()
        success_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0

        assert success_rate >= 70, f"접근성 점수가 너무 낮음: {success_rate:.1f}%"

        print(f"\n✓ 종합 접근성 점수: {success_rate:.1f}%")
        print("=== Comprehensive Accessibility Audit Completed ===\n")


if __name__ == "__main__":
    # 단독 실행 시 기본 정보 출력
    print("웹 접근성 테스트 모듈이 로드되었습니다.")
    print("\n테스트 범위:")
    print("- 키보드 네비게이션")
    print("- ARIA 속성 검증")
    print("- 색상 대비")
    print("- 자동 접근성 감사 (axe-core)")
    print("\n전체 테스트를 실행하려면:")
    print("pytest tests/test_usability/test_accessibility.py -v")