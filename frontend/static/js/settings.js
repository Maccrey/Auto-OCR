/**
 * K-OCR Web Corrector - Settings JavaScript
 * 설정 패널 관리 및 사용자 설정 기능
 */

window.OCRApp.Settings = {
  // 기본 설정값
  defaultSettings: {
    ocrEngine: 'paddleocr',
    preprocessing: {
      enabled: true,
      grayscaleConvert: true,
      contrastEnhance: true,
      deskewCorrection: false,
      noiseRemoval: false
    },
    textCorrection: {
      enabled: true,
      spacingCorrection: true,
      spellingCorrection: false
    },
    advanced: {
      imageDpi: 300,
      confidenceThreshold: 0.8
    }
  },

  // 현재 설정값
  currentSettings: {},

  // 초기화
  init() {
    console.log('Settings 모듈 초기화 중...');

    this.setupSettingsToggle();
    this.setupPreprocessingControls();
    this.setupOCREngineSelection();
    this.setupTextCorrectionControls();
    this.setupAdvancedSettings();
    this.setupSettingsActions();

    // 저장된 설정 불러오기
    this.loadSettings();

    // UI에 설정 적용
    this.applySettingsToUI();

    console.log('Settings 모듈 초기화 완료');
  },

  // 설정 토글 설정
  setupSettingsToggle() {
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsContent = document.getElementById('settings-content');

    if (!settingsToggle || !settingsContent) return;

    settingsToggle.addEventListener('click', () => {
      const isExpanded = settingsToggle.classList.contains('expanded');

      if (isExpanded) {
        this.collapseSettings();
      } else {
        this.expandSettings();
      }
    });
  },

  // 설정 패널 확장
  expandSettings() {
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsContent = document.getElementById('settings-content');
    const toggleIcon = settingsToggle?.querySelector('i');

    if (settingsContent) {
      settingsContent.style.display = 'block';
      settingsContent.style.maxHeight = settingsContent.scrollHeight + 'px';
    }

    if (settingsToggle) {
      settingsToggle.classList.add('expanded');
    }

    if (toggleIcon) {
      toggleIcon.style.transform = 'rotate(180deg)';
    }

    // 부드러운 스크롤 애니메이션
    setTimeout(() => {
      if (settingsContent) {
        settingsContent.style.maxHeight = 'none';
      }
    }, 300);
  },

  // 설정 패널 축소
  collapseSettings() {
    const settingsToggle = document.getElementById('settings-toggle');
    const settingsContent = document.getElementById('settings-content');
    const toggleIcon = settingsToggle?.querySelector('i');

    if (settingsContent) {
      settingsContent.style.maxHeight = settingsContent.scrollHeight + 'px';

      // 강제 리플로우
      settingsContent.offsetHeight;

      settingsContent.style.maxHeight = '0';
      setTimeout(() => {
        settingsContent.style.display = 'none';
      }, 300);
    }

    if (settingsToggle) {
      settingsToggle.classList.remove('expanded');
    }

    if (toggleIcon) {
      toggleIcon.style.transform = 'rotate(0deg)';
    }
  },

  // 전처리 컨트롤 설정
  setupPreprocessingControls() {
    const enablePreprocessing = document.getElementById('enable-preprocessing');
    const preprocessingDetails = document.getElementById('preprocessing-details');

    if (enablePreprocessing) {
      enablePreprocessing.addEventListener('change', (e) => {
        const enabled = e.target.checked;

        this.currentSettings.preprocessing.enabled = enabled;

        // 세부 옵션들 활성화/비활성화
        this.togglePreprocessingDetails(enabled);

        this.saveSettings();
      });
    }

    // 세부 전처리 옵션들
    const preprocessingOptions = [
      'grayscale-convert',
      'contrast-enhance',
      'deskew-correction',
      'noise-removal'
    ];

    preprocessingOptions.forEach(optionId => {
      const checkbox = document.getElementById(optionId);
      if (checkbox) {
        checkbox.addEventListener('change', (e) => {
          const settingKey = this.getSettingKeyFromId(optionId);
          if (settingKey) {
            this.currentSettings.preprocessing[settingKey] = e.target.checked;
            this.saveSettings();
          }
        });
      }
    });

    // 전처리 정보 버튼
    const preprocessingInfo = document.getElementById('preprocessing-info');
    if (preprocessingInfo) {
      preprocessingInfo.addEventListener('click', () => {
        this.showPreprocessingInfo();
      });
    }
  },

  // 전처리 세부사항 토글
  togglePreprocessingDetails(enabled) {
    const preprocessingDetails = document.getElementById('preprocessing-details');
    const checkboxes = preprocessingDetails?.querySelectorAll('input[type="checkbox"]');

    if (preprocessingDetails) {
      preprocessingDetails.style.opacity = enabled ? '1' : '0.5';
    }

    if (checkboxes) {
      checkboxes.forEach(checkbox => {
        checkbox.disabled = !enabled;
      });
    }
  },

  // OCR 엔진 선택 설정
  setupOCREngineSelection() {
    const ocrEngineSelect = document.getElementById('ocr-engine');

    if (ocrEngineSelect) {
      ocrEngineSelect.addEventListener('change', (e) => {
        const selectedEngine = e.target.value;

        this.currentSettings.ocrEngine = selectedEngine;
        this.saveSettings();

        // 엔진별 권장사항 표시
        this.showEngineRecommendations(selectedEngine);
      });
    }
  },

  // 텍스트 교정 컨트롤 설정
  setupTextCorrectionControls() {
    const enableCorrection = document.getElementById('enable-correction');
    const correctionDetails = document.getElementById('correction-details');

    if (enableCorrection) {
      enableCorrection.addEventListener('change', (e) => {
        const enabled = e.target.checked;

        this.currentSettings.textCorrection.enabled = enabled;

        // 세부 옵션들 활성화/비활성화
        this.toggleCorrectionDetails(enabled);

        this.saveSettings();
      });
    }

    // 세부 교정 옵션들
    const correctionOptions = [
      'spacing-correction',
      'spelling-correction'
    ];

    correctionOptions.forEach(optionId => {
      const checkbox = document.getElementById(optionId);
      if (checkbox) {
        checkbox.addEventListener('change', (e) => {
          const settingKey = this.getSettingKeyFromId(optionId);
          if (settingKey) {
            this.currentSettings.textCorrection[settingKey] = e.target.checked;
            this.saveSettings();
          }
        });
      }
    });
  },

  // 교정 세부사항 토글
  toggleCorrectionDetails(enabled) {
    const correctionDetails = document.getElementById('correction-details');
    const checkboxes = correctionDetails?.querySelectorAll('input[type="checkbox"]');

    if (correctionDetails) {
      correctionDetails.style.opacity = enabled ? '1' : '0.5';
    }

    if (checkboxes) {
      checkboxes.forEach(checkbox => {
        checkbox.disabled = !enabled;
      });
    }
  },

  // 고급 설정 설정
  setupAdvancedSettings() {
    const advancedToggle = document.getElementById('advanced-toggle');
    const advancedContent = document.getElementById('advanced-content');

    if (advancedToggle) {
      advancedToggle.addEventListener('click', () => {
        const isExpanded = advancedToggle.classList.contains('expanded');

        if (isExpanded) {
          this.collapseAdvancedSettings();
        } else {
          this.expandAdvancedSettings();
        }
      });
    }

    // DPI 설정
    const imageDpiSelect = document.getElementById('image-dpi');
    if (imageDpiSelect) {
      imageDpiSelect.addEventListener('change', (e) => {
        this.currentSettings.advanced.imageDpi = parseInt(e.target.value);
        this.saveSettings();
      });
    }

    // 신뢰도 임계값 설정
    const confidenceThreshold = document.getElementById('confidence-threshold');
    const confidenceValue = document.getElementById('confidence-value');

    if (confidenceThreshold) {
      confidenceThreshold.addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        this.currentSettings.advanced.confidenceThreshold = value;

        if (confidenceValue) {
          confidenceValue.textContent = Math.round(value * 100) + '%';
        }

        this.saveSettings();
      });
    }
  },

  // 고급 설정 확장
  expandAdvancedSettings() {
    const advancedToggle = document.getElementById('advanced-toggle');
    const advancedContent = document.getElementById('advanced-content');
    const toggleIcon = advancedToggle?.querySelector('i');

    if (advancedContent) {
      advancedContent.style.display = 'block';
      advancedContent.style.maxHeight = advancedContent.scrollHeight + 'px';
    }

    if (advancedToggle) {
      advancedToggle.classList.add('expanded');
    }

    if (toggleIcon) {
      toggleIcon.style.transform = 'rotate(180deg)';
    }

    setTimeout(() => {
      if (advancedContent) {
        advancedContent.style.maxHeight = 'none';
      }
    }, 300);
  },

  // 고급 설정 축소
  collapseAdvancedSettings() {
    const advancedToggle = document.getElementById('advanced-toggle');
    const advancedContent = document.getElementById('advanced-content');
    const toggleIcon = advancedToggle?.querySelector('i');

    if (advancedContent) {
      advancedContent.style.maxHeight = advancedContent.scrollHeight + 'px';
      advancedContent.offsetHeight; // 강제 리플로우
      advancedContent.style.maxHeight = '0';

      setTimeout(() => {
        advancedContent.style.display = 'none';
      }, 300);
    }

    if (advancedToggle) {
      advancedToggle.classList.remove('expanded');
    }

    if (toggleIcon) {
      toggleIcon.style.transform = 'rotate(0deg)';
    }
  },

  // 설정 액션 설정
  setupSettingsActions() {
    const saveButton = document.getElementById('settings-save');
    const resetButton = document.getElementById('settings-reset');

    if (saveButton) {
      saveButton.addEventListener('click', () => {
        this.saveSettings();
        window.OCRApp.showToast('설정이 저장되었습니다.', 'success');
      });
    }

    if (resetButton) {
      resetButton.addEventListener('click', () => {
        this.resetSettings();
      });
    }
  },

  // 설정 저장
  saveSettings() {
    try {
      const settingsJson = JSON.stringify(this.currentSettings);
      localStorage.setItem('ocrSettings', settingsJson);

      // 전역 상태에도 반영
      if (window.OCRApp.state) {
        window.OCRApp.state.settings = { ...this.currentSettings };
      }

      console.log('설정 저장됨:', this.currentSettings);
    } catch (error) {
      console.error('설정 저장 오류:', error);
      window.OCRApp.showToast('설정 저장에 실패했습니다.', 'error');
    }
  },

  // 설정 불러오기
  loadSettings() {
    try {
      const savedSettings = localStorage.getItem('ocrSettings');

      if (savedSettings) {
        const parsedSettings = JSON.parse(savedSettings);
        this.currentSettings = this.mergeSettings(this.defaultSettings, parsedSettings);
      } else {
        this.currentSettings = { ...this.defaultSettings };
      }

      // 전역 상태에도 반영
      if (window.OCRApp.state) {
        window.OCRApp.state.settings = { ...this.currentSettings };
      }

      console.log('설정 불러옴:', this.currentSettings);
    } catch (error) {
      console.error('설정 불러오기 오류:', error);
      this.currentSettings = { ...this.defaultSettings };
    }
  },

  // 설정 병합 (기본값 + 저장된 값)
  mergeSettings(defaultSettings, savedSettings) {
    const merged = JSON.parse(JSON.stringify(defaultSettings));

    const deepMerge = (target, source) => {
      for (const key in source) {
        if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
          if (!target[key]) target[key] = {};
          deepMerge(target[key], source[key]);
        } else {
          target[key] = source[key];
        }
      }
    };

    deepMerge(merged, savedSettings);
    return merged;
  },

  // 설정 초기화
  resetSettings() {
    const confirmed = confirm(
      '설정을 기본값으로 초기화하시겠습니까?\n현재 설정이 모두 삭제됩니다.'
    );

    if (confirmed) {
      this.currentSettings = { ...this.defaultSettings };
      this.saveSettings();
      this.applySettingsToUI();

      window.OCRApp.showToast('설정이 기본값으로 초기화되었습니다.', 'info');
    }
  },

  // UI에 설정 적용
  applySettingsToUI() {
    // OCR 엔진 선택
    const ocrEngineSelect = document.getElementById('ocr-engine');
    if (ocrEngineSelect) {
      ocrEngineSelect.value = this.currentSettings.ocrEngine;
    }

    // 전처리 설정
    const enablePreprocessing = document.getElementById('enable-preprocessing');
    if (enablePreprocessing) {
      enablePreprocessing.checked = this.currentSettings.preprocessing.enabled;
      this.togglePreprocessingDetails(this.currentSettings.preprocessing.enabled);
    }

    // 전처리 세부 옵션
    this.applyCheckboxSetting('grayscale-convert', this.currentSettings.preprocessing.grayscaleConvert);
    this.applyCheckboxSetting('contrast-enhance', this.currentSettings.preprocessing.contrastEnhance);
    this.applyCheckboxSetting('deskew-correction', this.currentSettings.preprocessing.deskewCorrection);
    this.applyCheckboxSetting('noise-removal', this.currentSettings.preprocessing.noiseRemoval);

    // 텍스트 교정 설정
    const enableCorrection = document.getElementById('enable-correction');
    if (enableCorrection) {
      enableCorrection.checked = this.currentSettings.textCorrection.enabled;
      this.toggleCorrectionDetails(this.currentSettings.textCorrection.enabled);
    }

    // 텍스트 교정 세부 옵션
    this.applyCheckboxSetting('spacing-correction', this.currentSettings.textCorrection.spacingCorrection);
    this.applyCheckboxSetting('spelling-correction', this.currentSettings.textCorrection.spellingCorrection);

    // 고급 설정
    const imageDpiSelect = document.getElementById('image-dpi');
    if (imageDpiSelect) {
      imageDpiSelect.value = this.currentSettings.advanced.imageDpi.toString();
    }

    const confidenceThreshold = document.getElementById('confidence-threshold');
    const confidenceValue = document.getElementById('confidence-value');
    if (confidenceThreshold) {
      confidenceThreshold.value = this.currentSettings.advanced.confidenceThreshold.toString();

      if (confidenceValue) {
        confidenceValue.textContent = Math.round(this.currentSettings.advanced.confidenceThreshold * 100) + '%';
      }
    }
  },

  // 체크박스 설정 적용
  applyCheckboxSetting(elementId, value) {
    const checkbox = document.getElementById(elementId);
    if (checkbox) {
      checkbox.checked = value;
    }
  },

  // 설정 키 변환 (ID -> 설정 키)
  getSettingKeyFromId(elementId) {
    const keyMap = {
      'grayscale-convert': 'grayscaleConvert',
      'contrast-enhance': 'contrastEnhance',
      'deskew-correction': 'deskewCorrection',
      'noise-removal': 'noiseRemoval',
      'spacing-correction': 'spacingCorrection',
      'spelling-correction': 'spellingCorrection'
    };

    return keyMap[elementId];
  },

  // 전처리 정보 표시
  showPreprocessingInfo() {
    const infoMessage = `
이미지 전처리 옵션:

• 흑백 변환: 컬러 이미지를 흑백으로 변환하여 텍스트 인식률 향상
• 대비 향상 (CLAHE): 이미지 대비를 개선하여 글자를 더 선명하게 만듦
• 기울기 보정: 스캔된 문서의 기울어진 각도를 자동으로 보정
• 노이즈 제거: 이미지의 잡음을 제거하여 깔끔한 텍스트 추출

권장: 흑백 변환과 대비 향상은 대부분의 문서에서 효과적입니다.
    `.trim();

    alert(infoMessage);
  },

  // 엔진별 권장사항 표시
  showEngineRecommendations(engine) {
    let message = '';

    switch (engine) {
      case 'paddleocr':
        message = 'PaddleOCR: 한국어 인식률이 우수하며, 다양한 폰트를 잘 인식합니다. (권장)';
        break;
      case 'tesseract':
        message = 'Tesseract: 오픈소스 OCR 엔진으로 널리 사용되며, 깔끔한 문서에 효과적입니다.';
        break;
      case 'ensemble':
        message = '앙상블: 두 엔진의 결과를 조합하여 더 정확한 결과를 제공하지만, 처리 시간이 더 오래 걸립니다.';
        break;
    }

    if (message) {
      window.OCRApp.showToast(message, 'info', 3000);
    }
  },

  // 현재 설정 가져오기
  getCurrentSettings() {
    return { ...this.currentSettings };
  },

  // 설정 검증
  validateSettings(settings) {
    const validEngines = ['paddleocr', 'tesseract', 'ensemble'];
    const validDpis = [150, 300, 600];

    // OCR 엔진 검증
    if (!validEngines.includes(settings.ocrEngine)) {
      return { valid: false, error: '유효하지 않은 OCR 엔진입니다.' };
    }

    // DPI 검증
    if (!validDpis.includes(settings.advanced.imageDpi)) {
      return { valid: false, error: '유효하지 않은 DPI 값입니다.' };
    }

    // 신뢰도 임계값 검증
    const threshold = settings.advanced.confidenceThreshold;
    if (threshold < 0.1 || threshold > 1.0) {
      return { valid: false, error: '신뢰도 임계값은 0.1 ~ 1.0 사이여야 합니다.' };
    }

    return { valid: true };
  },

  // 설정 내보내기
  exportSettings() {
    try {
      const settingsJson = JSON.stringify(this.currentSettings, null, 2);
      const blob = new Blob([settingsJson], { type: 'application/json' });
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = 'ocr-settings.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);

      URL.revokeObjectURL(url);

      window.OCRApp.showToast('설정이 내보내기되었습니다.', 'success');
    } catch (error) {
      console.error('설정 내보내기 오류:', error);
      window.OCRApp.showToast('설정 내보내기에 실패했습니다.', 'error');
    }
  },

  // 설정 가져오기
  importSettings(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const importedSettings = JSON.parse(e.target.result);
          const validation = this.validateSettings(importedSettings);

          if (!validation.valid) {
            reject(new Error(validation.error));
            return;
          }

          this.currentSettings = this.mergeSettings(this.defaultSettings, importedSettings);
          this.saveSettings();
          this.applySettingsToUI();

          window.OCRApp.showToast('설정을 성공적으로 가져왔습니다.', 'success');
          resolve(this.currentSettings);
        } catch (error) {
          reject(new Error('유효하지 않은 설정 파일입니다.'));
        }
      };

      reader.onerror = () => {
        reject(new Error('파일을 읽을 수 없습니다.'));
      };

      reader.readAsText(file);
    });
  },

  // 키보드 단축키 처리
  handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + S: 설정 저장
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      this.saveSettings();
      window.OCRApp.showToast('설정이 저장되었습니다.', 'success');
    }

    // Ctrl/Cmd + R: 설정 초기화
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
      e.preventDefault();
      this.resetSettings();
    }
  }
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  if (window.OCRApp && window.OCRApp.Settings) {
    window.OCRApp.Settings.init();

    // 키보드 단축키 등록
    document.addEventListener('keydown', window.OCRApp.Settings.handleKeyboardShortcuts.bind(window.OCRApp.Settings));
  }
});

// 설정 변경 이벤트 발생
window.addEventListener('settingsChanged', (event) => {
  const { settings } = event.detail;
  console.log('설정 변경됨:', settings);
});

// 페이지 언로드 시 설정 자동 저장
window.addEventListener('beforeunload', () => {
  if (window.OCRApp && window.OCRApp.Settings) {
    window.OCRApp.Settings.saveSettings();
  }
});