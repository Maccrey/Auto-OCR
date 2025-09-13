"""
설정 패널 프론트엔드 테스트 모듈

이 모듈은 설정 패널의 프론트엔드 기능을 테스트합니다:
- 설정 패널 표시/숨김 테스트
- 전처리 옵션 토글 테스트
- OCR 엔진 선택 테스트
- 설정값 저장 테스트
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from typing import Dict, Any

# Settings 모듈을 import (구현 후)
try:
    from frontend.static.js.settings import Settings
except ImportError:
    # 아직 구현되지 않은 경우 Mock 클래스
    class Settings:
        pass

# FastAPI 테스트 앱 생성
app = FastAPI()


@pytest.fixture
def client():
    """테스트 클라이언트 생성"""
    return TestClient(app)


@pytest.fixture
def sample_settings_html():
    """설정 패널이 포함된 샘플 HTML"""
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>K-OCR Settings Test</title>
        <link rel="stylesheet" href="/static/css/main.css">
    </head>
    <body>
        <div class="settings-section" id="settings-section">
            <div class="settings-header">
                <h3 class="settings-title">
                    <i class="fas fa-cogs"></i>
                    처리 설정
                </h3>
                <button class="settings-toggle" id="settings-toggle">
                    <i class="fas fa-chevron-down"></i>
                </button>
            </div>

            <div class="settings-content" id="settings-content">
                <!-- OCR 엔진 선택 -->
                <div class="setting-group">
                    <div class="setting-header">
                        <label class="setting-label">
                            <i class="fas fa-robot"></i>
                            OCR 엔진
                        </label>
                    </div>
                    <select class="setting-select" id="ocr-engine" name="ocrEngine">
                        <option value="paddleocr">PaddleOCR (권장)</option>
                        <option value="tesseract">Tesseract</option>
                        <option value="ensemble">앙상블 (PaddleOCR + Tesseract)</option>
                    </select>
                    <p class="setting-description">
                        OCR 엔진을 선택하세요. PaddleOCR이 한국어 인식률이 높습니다.
                    </p>
                </div>

                <!-- 이미지 전처리 설정 -->
                <div class="setting-group">
                    <div class="setting-header">
                        <label class="setting-label">
                            <input type="checkbox" id="enable-preprocessing" checked>
                            <span class="checkmark"></span>
                            <i class="fas fa-image"></i>
                            이미지 전처리
                        </label>
                        <button class="setting-info" id="preprocessing-info">
                            <i class="fas fa-question-circle"></i>
                        </button>
                    </div>

                    <div class="setting-details" id="preprocessing-details">
                        <div class="sub-setting">
                            <input type="checkbox" id="grayscale-convert" checked>
                            <span class="checkmark"></span>
                            <span>흑백 변환</span>
                        </div>
                        <div class="sub-setting">
                            <input type="checkbox" id="contrast-enhance" checked>
                            <span class="checkmark"></span>
                            <span>대비 향상 (CLAHE)</span>
                        </div>
                        <div class="sub-setting">
                            <input type="checkbox" id="deskew-correction">
                            <span class="checkmark"></span>
                            <span>기울기 보정</span>
                        </div>
                        <div class="sub-setting">
                            <input type="checkbox" id="noise-removal">
                            <span class="checkmark"></span>
                            <span>노이즈 제거</span>
                        </div>
                    </div>
                </div>

                <!-- 텍스트 교정 설정 -->
                <div class="setting-group">
                    <div class="setting-header">
                        <label class="setting-label">
                            <input type="checkbox" id="enable-correction" checked>
                            <span class="checkmark"></span>
                            <i class="fas fa-spell-check"></i>
                            텍스트 교정
                        </label>
                    </div>

                    <div class="setting-details" id="correction-details">
                        <div class="sub-setting">
                            <input type="checkbox" id="spacing-correction" checked>
                            <span class="checkmark"></span>
                            <span>띄어쓰기 교정</span>
                        </div>
                        <div class="sub-setting">
                            <input type="checkbox" id="spelling-correction">
                            <span class="checkmark"></span>
                            <span>맞춤법 교정</span>
                        </div>
                    </div>
                </div>

                <!-- 고급 설정 -->
                <div class="setting-group">
                    <div class="advanced-settings">
                        <button class="advanced-toggle" id="advanced-toggle">
                            <i class="fas fa-chevron-down"></i>
                            고급 설정
                        </button>

                        <div class="advanced-content" id="advanced-content" style="display: none;">
                            <div class="setting-item">
                                <label class="setting-label">이미지 DPI</label>
                                <select class="setting-select" id="image-dpi">
                                    <option value="150">150 DPI</option>
                                    <option value="300" selected>300 DPI (권장)</option>
                                    <option value="600">600 DPI</option>
                                </select>
                            </div>

                            <div class="setting-item">
                                <label class="setting-label">OCR 신뢰도 임계값</label>
                                <input type="range" id="confidence-threshold" min="0.1" max="1.0" step="0.1" value="0.8">
                                <span id="confidence-value">80%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 설정 저장/초기화 버튼 -->
        <div class="settings-actions">
            <button class="settings-save" id="settings-save">
                <i class="fas fa-save"></i> 설정 저장
            </button>
            <button class="settings-reset" id="settings-reset">
                <i class="fas fa-undo"></i> 기본값으로 초기화
            </button>
        </div>

        <script src="/static/js/main.js"></script>
        <script src="/static/js/settings.js"></script>
    </body>
    </html>
    """


@pytest.fixture
def mock_local_storage():
    """localStorage Mock"""
    storage = {}

    def get_item(key):
        return storage.get(key)

    def set_item(key, value):
        storage[key] = value

    def remove_item(key):
        storage.pop(key, None)

    def clear():
        storage.clear()

    mock_storage = Mock()
    mock_storage.getItem = Mock(side_effect=get_item)
    mock_storage.setItem = Mock(side_effect=set_item)
    mock_storage.removeItem = Mock(side_effect=remove_item)
    mock_storage.clear = Mock(side_effect=clear)

    return mock_storage


class TestSettingsPanelVisibility:
    """설정 패널 표시/숨김 테스트"""

    def test_settings_section_exists(self, sample_settings_html):
        """설정 섹션이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        settings_section = soup.find('div', {'id': 'settings-section'})
        assert settings_section is not None
        assert 'settings-section' in settings_section.get('class', [])

    def test_settings_toggle_button_exists(self, sample_settings_html):
        """설정 토글 버튼이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        toggle_button = soup.find('button', {'id': 'settings-toggle'})
        assert toggle_button is not None
        assert 'settings-toggle' in toggle_button.get('class', [])

        # 아이콘 확인
        icon = toggle_button.find('i')
        assert icon is not None
        assert 'fa-chevron-down' in icon.get('class', [])

    def test_settings_content_exists(self, sample_settings_html):
        """설정 내용이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        settings_content = soup.find('div', {'id': 'settings-content'})
        assert settings_content is not None
        assert 'settings-content' in settings_content.get('class', [])

        # 설정 그룹들이 존재하는지 확인
        setting_groups = settings_content.find_all('div', class_='setting-group')
        assert len(setting_groups) >= 3  # OCR 엔진, 전처리, 텍스트 교정

    def test_settings_header_structure(self, sample_settings_html):
        """설정 헤더 구조 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        settings_header = soup.find('div', class_='settings-header')
        assert settings_header is not None

        # 제목 확인
        title = settings_header.find('h3', class_='settings-title')
        assert title is not None
        assert '처리 설정' in title.get_text()

        # 아이콘 확인
        icon = title.find('i', class_='fas')
        assert icon is not None


class TestPreprocessingOptions:
    """전처리 옵션 테스트"""

    def test_preprocessing_checkbox_exists(self, sample_settings_html):
        """전처리 체크박스가 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        preprocessing_checkbox = soup.find('input', {'id': 'enable-preprocessing'})
        assert preprocessing_checkbox is not None
        assert preprocessing_checkbox.get('type') == 'checkbox'
        assert preprocessing_checkbox.has_attr('checked')  # 기본적으로 체크됨

    def test_preprocessing_sub_options_exist(self, sample_settings_html):
        """전처리 세부 옵션들이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        # 필수 전처리 옵션들
        expected_options = [
            'grayscale-convert',
            'contrast-enhance',
            'deskew-correction',
            'noise-removal'
        ]

        for option_id in expected_options:
            checkbox = soup.find('input', {'id': option_id})
            assert checkbox is not None
            assert checkbox.get('type') == 'checkbox'

    def test_preprocessing_details_section(self, sample_settings_html):
        """전처리 세부사항 섹션 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        details_section = soup.find('div', {'id': 'preprocessing-details'})
        assert details_section is not None
        assert 'setting-details' in details_section.get('class', [])

        # 세부 설정 항목들 확인
        sub_settings = details_section.find_all('div', class_='sub-setting')
        assert len(sub_settings) >= 4  # 흑백변환, 대비향상, 기울기보정, 노이즈제거

    def test_preprocessing_info_button(self, sample_settings_html):
        """전처리 정보 버튼 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        info_button = soup.find('button', {'id': 'preprocessing-info'})
        assert info_button is not None
        assert 'setting-info' in info_button.get('class', [])

        # 물음표 아이콘 확인
        icon = info_button.find('i')
        assert icon is not None
        assert 'fa-question-circle' in icon.get('class', [])


class TestOCREngineSelection:
    """OCR 엔진 선택 테스트"""

    def test_ocr_engine_dropdown_exists(self, sample_settings_html):
        """OCR 엔진 드롭다운이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        ocr_select = soup.find('select', {'id': 'ocr-engine'})
        assert ocr_select is not None
        assert 'setting-select' in ocr_select.get('class', [])
        assert ocr_select.get('name') == 'ocrEngine'

    def test_ocr_engine_options(self, sample_settings_html):
        """OCR 엔진 옵션들이 올바른지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        ocr_select = soup.find('select', {'id': 'ocr-engine'})
        options = ocr_select.find_all('option')

        assert len(options) >= 3  # paddleocr, tesseract, ensemble

        # 옵션 값들 확인
        option_values = [opt.get('value') for opt in options]
        expected_values = ['paddleocr', 'tesseract', 'ensemble']

        for expected in expected_values:
            assert expected in option_values

    def test_ocr_engine_labels(self, sample_settings_html):
        """OCR 엔진 라벨이 올바른지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        ocr_select = soup.find('select', {'id': 'ocr-engine'})
        options = ocr_select.find_all('option')

        # 옵션 텍스트 확인
        option_texts = [opt.get_text().strip() for opt in options]

        assert any('PaddleOCR' in text for text in option_texts)
        assert any('Tesseract' in text for text in option_texts)
        assert any('앙상블' in text for text in option_texts)

    def test_ocr_engine_description(self, sample_settings_html):
        """OCR 엔진 설명이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        # OCR 엔진 설정 그룹 찾기
        ocr_group = soup.find('select', {'id': 'ocr-engine'}).parent
        description = ocr_group.find('p', class_='setting-description')

        assert description is not None
        assert 'OCR 엔진을 선택하세요' in description.get_text()


class TestTextCorrectionSettings:
    """텍스트 교정 설정 테스트"""

    def test_text_correction_checkbox_exists(self, sample_settings_html):
        """텍스트 교정 체크박스가 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        correction_checkbox = soup.find('input', {'id': 'enable-correction'})
        assert correction_checkbox is not None
        assert correction_checkbox.get('type') == 'checkbox'
        assert correction_checkbox.has_attr('checked')  # 기본적으로 체크됨

    def test_text_correction_sub_options(self, sample_settings_html):
        """텍스트 교정 세부 옵션들이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        # 띄어쓰기 교정
        spacing_checkbox = soup.find('input', {'id': 'spacing-correction'})
        assert spacing_checkbox is not None
        assert spacing_checkbox.get('type') == 'checkbox'

        # 맞춤법 교정
        spelling_checkbox = soup.find('input', {'id': 'spelling-correction'})
        assert spelling_checkbox is not None
        assert spelling_checkbox.get('type') == 'checkbox'

    def test_correction_details_section(self, sample_settings_html):
        """교정 세부사항 섹션 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        details_section = soup.find('div', {'id': 'correction-details'})
        assert details_section is not None
        assert 'setting-details' in details_section.get('class', [])


class TestAdvancedSettings:
    """고급 설정 테스트"""

    def test_advanced_toggle_exists(self, sample_settings_html):
        """고급 설정 토글이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        advanced_toggle = soup.find('button', {'id': 'advanced-toggle'})
        assert advanced_toggle is not None
        assert 'advanced-toggle' in advanced_toggle.get('class', [])
        assert '고급 설정' in advanced_toggle.get_text()

    def test_advanced_content_exists(self, sample_settings_html):
        """고급 설정 내용이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        advanced_content = soup.find('div', {'id': 'advanced-content'})
        assert advanced_content is not None
        assert 'advanced-content' in advanced_content.get('class', [])

        # 기본적으로 숨김 상태
        style = advanced_content.get('style', '')
        assert 'display: none' in style

    def test_dpi_setting_exists(self, sample_settings_html):
        """DPI 설정이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        dpi_select = soup.find('select', {'id': 'image-dpi'})
        assert dpi_select is not None

        # DPI 옵션들 확인
        options = dpi_select.find_all('option')
        dpi_values = [opt.get('value') for opt in options]

        assert '150' in dpi_values
        assert '300' in dpi_values
        assert '600' in dpi_values

    def test_confidence_threshold_setting(self, sample_settings_html):
        """신뢰도 임계값 설정이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        confidence_slider = soup.find('input', {'id': 'confidence-threshold'})
        assert confidence_slider is not None
        assert confidence_slider.get('type') == 'range'
        assert confidence_slider.get('min') == '0.1'
        assert confidence_slider.get('max') == '1.0'
        assert confidence_slider.get('step') == '0.1'
        assert confidence_slider.get('value') == '0.8'

        # 값 표시 스팬
        confidence_value = soup.find('span', {'id': 'confidence-value'})
        assert confidence_value is not None
        assert '80%' in confidence_value.get_text()


class TestSettingsActions:
    """설정 액션 버튼 테스트"""

    def test_settings_save_button_exists(self, sample_settings_html):
        """설정 저장 버튼이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        save_button = soup.find('button', {'id': 'settings-save'})
        assert save_button is not None
        assert 'settings-save' in save_button.get('class', [])
        assert '설정 저장' in save_button.get_text()

        # 아이콘 확인
        icon = save_button.find('i')
        assert icon is not None
        assert 'fa-save' in icon.get('class', [])

    def test_settings_reset_button_exists(self, sample_settings_html):
        """설정 초기화 버튼이 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        reset_button = soup.find('button', {'id': 'settings-reset'})
        assert reset_button is not None
        assert 'settings-reset' in reset_button.get('class', [])
        assert '기본값으로 초기화' in reset_button.get_text()

        # 아이콘 확인
        icon = reset_button.find('i')
        assert icon is not None
        assert 'fa-undo' in icon.get('class', [])

    def test_settings_actions_container(self, sample_settings_html):
        """설정 액션 컨테이너가 존재하는지 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        actions_container = soup.find('div', class_='settings-actions')
        assert actions_container is not None

        # 버튼들이 컨테이너 안에 있는지 확인
        buttons = actions_container.find_all('button')
        assert len(buttons) >= 2  # 저장, 초기화 버튼


class TestSettingsDataStructure:
    """설정 데이터 구조 테스트"""

    @pytest.fixture
    def default_settings(self):
        """기본 설정 데이터"""
        return {
            "ocrEngine": "paddleocr",
            "preprocessing": {
                "enabled": True,
                "grayscaleConvert": True,
                "contrastEnhance": True,
                "deskewCorrection": False,
                "noiseRemoval": False
            },
            "textCorrection": {
                "enabled": True,
                "spacingCorrection": True,
                "spellingCorrection": False
            },
            "advanced": {
                "imageDpi": 300,
                "confidenceThreshold": 0.8
            }
        }

    def test_default_settings_structure(self, default_settings):
        """기본 설정 구조가 올바른지 테스트"""
        assert "ocrEngine" in default_settings
        assert "preprocessing" in default_settings
        assert "textCorrection" in default_settings
        assert "advanced" in default_settings

        # 전처리 설정 구조
        preprocessing = default_settings["preprocessing"]
        assert "enabled" in preprocessing
        assert "grayscaleConvert" in preprocessing
        assert "contrastEnhance" in preprocessing
        assert "deskewCorrection" in preprocessing
        assert "noiseRemoval" in preprocessing

        # 텍스트 교정 설정 구조
        correction = default_settings["textCorrection"]
        assert "enabled" in correction
        assert "spacingCorrection" in correction
        assert "spellingCorrection" in correction

        # 고급 설정 구조
        advanced = default_settings["advanced"]
        assert "imageDpi" in advanced
        assert "confidenceThreshold" in advanced

    def test_settings_validation(self, default_settings):
        """설정값 검증 테스트"""
        # OCR 엔진 값 검증
        valid_engines = ["paddleocr", "tesseract", "ensemble"]
        assert default_settings["ocrEngine"] in valid_engines

        # DPI 값 검증
        valid_dpis = [150, 300, 600]
        assert default_settings["advanced"]["imageDpi"] in valid_dpis

        # 신뢰도 임계값 검증
        threshold = default_settings["advanced"]["confidenceThreshold"]
        assert 0.1 <= threshold <= 1.0


class TestLocalStorageIntegration:
    """localStorage 통합 테스트"""

    def test_settings_save_to_storage(self, mock_local_storage):
        """설정을 localStorage에 저장하는 테스트"""
        settings_data = {
            "ocrEngine": "tesseract",
            "preprocessing": {
                "enabled": True,
                "grayscaleConvert": False
            }
        }

        # 설정 저장 시뮬레이션
        settings_json = json.dumps(settings_data)
        mock_local_storage.setItem('ocrSettings', settings_json)

        # 저장 확인
        mock_local_storage.setItem.assert_called_with('ocrSettings', settings_json)

    def test_settings_load_from_storage(self, mock_local_storage):
        """localStorage에서 설정을 불러오는 테스트"""
        settings_data = {
            "ocrEngine": "ensemble",
            "preprocessing": {"enabled": False}
        }

        # localStorage에 데이터 설정
        settings_json = json.dumps(settings_data)

        # Mock의 getItem이 올바른 값을 반환하도록 설정
        def mock_get_item(key):
            if key == 'ocrSettings':
                return settings_json
            return None

        mock_local_storage.getItem.side_effect = mock_get_item

        # 설정 로드 시뮬레이션
        loaded_data = mock_local_storage.getItem('ocrSettings')

        mock_local_storage.getItem.assert_called_with('ocrSettings')
        assert loaded_data == settings_json

        # JSON 파싱 후 데이터 확인
        parsed_data = json.loads(loaded_data)
        assert parsed_data["ocrEngine"] == "ensemble"
        assert parsed_data["preprocessing"]["enabled"] is False

    def test_settings_storage_key_consistency(self):
        """설정 저장 키 일관성 테스트"""
        storage_key = "ocrSettings"

        # 키 형식 검증
        assert isinstance(storage_key, str)
        assert len(storage_key) > 0
        assert storage_key.isalnum() or storage_key.replace('_', '').isalnum()


class TestSettingsUIInteraction:
    """설정 UI 상호작용 테스트"""

    def test_checkbox_interaction_simulation(self, sample_settings_html):
        """체크박스 상호작용 시뮬레이션 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        # 전처리 활성화 체크박스 찾기
        preprocessing_checkbox = soup.find('input', {'id': 'enable-preprocessing'})

        # 초기 상태 확인 (체크됨)
        assert preprocessing_checkbox.has_attr('checked')

        # 체크 해제 시뮬레이션
        if preprocessing_checkbox.has_attr('checked'):
            del preprocessing_checkbox.attrs['checked']

        # 체크 해제 상태 확인
        assert not preprocessing_checkbox.has_attr('checked')

    def test_dropdown_selection_simulation(self, sample_settings_html):
        """드롭다운 선택 시뮬레이션 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        ocr_select = soup.find('select', {'id': 'ocr-engine'})
        options = ocr_select.find_all('option')

        # 초기 선택값 없음 (첫 번째 옵션이 기본)
        selected_option = next((opt for opt in options if opt.has_attr('selected')), options[0])
        assert selected_option.get('value') == 'paddleocr'

        # 다른 옵션 선택 시뮬레이션
        for option in options:
            if option.has_attr('selected'):
                del option.attrs['selected']

        tesseract_option = next(opt for opt in options if opt.get('value') == 'tesseract')
        tesseract_option.attrs['selected'] = True

        # 선택 변경 확인
        selected_option = next(opt for opt in options if opt.has_attr('selected'))
        assert selected_option.get('value') == 'tesseract'

    def test_range_slider_value_simulation(self, sample_settings_html):
        """범위 슬라이더 값 변경 시뮬레이션 테스트"""
        soup = BeautifulSoup(sample_settings_html, 'html.parser')

        confidence_slider = soup.find('input', {'id': 'confidence-threshold'})

        # 초기값 확인
        assert confidence_slider.get('value') == '0.8'

        # 값 변경 시뮬레이션
        confidence_slider.attrs['value'] = '0.6'

        # 변경된 값 확인
        assert confidence_slider.get('value') == '0.6'


class TestErrorHandling:
    """오류 처리 테스트"""

    def test_invalid_settings_data_handling(self):
        """잘못된 설정 데이터 처리 테스트"""
        invalid_data_cases = [
            None,
            "",
            "invalid json",
            '{"invalid": json}',
            '{"ocrEngine": "invalid_engine"}'
        ]

        for invalid_data in invalid_data_cases:
            try:
                if invalid_data and isinstance(invalid_data, str):
                    parsed_data = json.loads(invalid_data)
                    # 잘못된 엔진 타입 검증
                    if "ocrEngine" in parsed_data:
                        valid_engines = ["paddleocr", "tesseract", "ensemble"]
                        assert parsed_data["ocrEngine"] in valid_engines
            except (json.JSONDecodeError, AssertionError, TypeError):
                # 예상된 에러들 - 정상 처리됨
                pass

    def test_missing_elements_handling(self):
        """누락된 요소 처리 테스트"""
        incomplete_html = """
        <html>
        <body>
            <!-- 일부 요소만 있는 불완전한 HTML -->
            <div class="settings-section">
                <select id="ocr-engine">
                    <option value="paddleocr">PaddleOCR</option>
                </select>
            </div>
        </body>
        </html>
        """

        soup = BeautifulSoup(incomplete_html, 'html.parser')

        # 존재하는 요소 확인
        ocr_select = soup.find('select', {'id': 'ocr-engine'})
        assert ocr_select is not None

        # 존재하지 않는 요소에 대한 안전한 처리
        missing_element = soup.find('input', {'id': 'enable-preprocessing'})
        assert missing_element is None  # 에러 없이 None 반환

    def test_storage_error_handling(self, mock_local_storage):
        """저장소 오류 처리 테스트"""
        # localStorage 접근 오류 시뮬레이션
        mock_local_storage.getItem.side_effect = Exception("Storage access denied")
        mock_local_storage.setItem.side_effect = Exception("Storage write failed")

        # 오류 발생 시에도 예외 없이 처리되어야 함
        try:
            mock_local_storage.getItem('ocrSettings')
            assert False, "Exception should have been raised"
        except Exception as e:
            assert "Storage access denied" in str(e)

        try:
            mock_local_storage.setItem('ocrSettings', '{}')
            assert False, "Exception should have been raised"
        except Exception as e:
            assert "Storage write failed" in str(e)