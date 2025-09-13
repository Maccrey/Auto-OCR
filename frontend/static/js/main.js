/**
 * K-OCR Web Corrector - Main JavaScript
 * 메인 애플리케이션 로직 및 전역 유틸리티
 */

// 전역 애플리케이션 객체
window.OCRApp = {
  // 애플리케이션 상태
  state: {
    currentSection: 'upload',
    uploadedFile: null,
    processId: null,
    isProcessing: false,
    settings: {
      preprocessing: {
        enabled: true,
        clahe: true,
        deskew: true,
        noiseRemoval: true
      },
      ocrEngine: 'paddle',
      textCorrection: {
        enabled: true,
        spacing: true,
        spelling: true
      },
      advanced: {
        dpi: 300,
        language: 'ko'
      }
    }
  },

  // 설정
  config: {
    apiBaseUrl: '/api',
    maxFileSize: 50 * 1024 * 1024, // 50MB
    supportedFormats: ['.pdf'],
    pollInterval: 2000, // 2초
    maxPollAttempts: 300 // 10분
  },

  // 초기화
  init() {
    console.log('K-OCR Web Corrector 초기화 중...');

    this.setupEventListeners();
    this.loadSettings();
    this.setupTooltips();
    this.checkBrowserSupport();

    console.log('초기화 완료');
  },

  // 이벤트 리스너 설정
  setupEventListeners() {
    // 설정 관련 이벤트
    document.addEventListener('change', this.handleSettingsChange.bind(this));

    // 고급 설정 토글
    const advancedToggle = document.getElementById('advanced-toggle');
    if (advancedToggle) {
      advancedToggle.addEventListener('click', this.toggleAdvancedSettings.bind(this));
    }

    // 버튼 이벤트들
    this.setupButtonEvents();

    // 키보드 단축키
    document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));

    // 페이지 이탈 확인
    window.addEventListener('beforeunload', this.handlePageUnload.bind(this));
  },

  // 버튼 이벤트 설정
  setupButtonEvents() {
    const buttons = {
      'new-upload-button': () => this.showSection('upload'),
      'retry-button': () => this.retryProcessing(),
      'back-to-upload-button': () => this.showSection('upload'),
      'copy-text-button': () => this.copyTextToClipboard(),
      'share-button': () => this.shareResult(),
      'preview-toggle': () => this.toggleTextPreview(),
      'cancel-button': () => this.cancelProcessing()
    };

    Object.entries(buttons).forEach(([id, handler]) => {
      const element = document.getElementById(id);
      if (element) {
        element.addEventListener('click', handler);
      }
    });
  },

  // 설정 변경 처리
  handleSettingsChange(event) {
    const target = event.target;
    if (!target.matches('input[type="checkbox"], select')) return;

    const settingId = target.id;
    const value = target.type === 'checkbox' ? target.checked : target.value;

    // 설정 상태 업데이트
    this.updateSetting(settingId, value);

    // 설정 저장
    this.saveSettings();

    // 의존 설정 처리
    this.handleSettingDependencies(settingId, value);
  },

  // 설정 업데이트
  updateSetting(settingId, value) {
    const settingMap = {
      'preprocessing-enabled': () => this.state.settings.preprocessing.enabled = value,
      'clahe-enabled': () => this.state.settings.preprocessing.clahe = value,
      'deskew-enabled': () => this.state.settings.preprocessing.deskew = value,
      'noise-removal': () => this.state.settings.preprocessing.noiseRemoval = value,
      'ocr-engine': () => this.state.settings.ocrEngine = value,
      'text-correction': () => this.state.settings.textCorrection.enabled = value,
      'spacing-correction': () => this.state.settings.textCorrection.spacing = value,
      'spelling-correction': () => this.state.settings.textCorrection.spelling = value,
      'dpi-setting': () => this.state.settings.advanced.dpi = parseInt(value),
      'language-model': () => this.state.settings.advanced.language = value
    };

    const updateFunction = settingMap[settingId];
    if (updateFunction) {
      updateFunction();
    }
  },

  // 설정 의존성 처리
  handleSettingDependencies(settingId, value) {
    switch (settingId) {
      case 'preprocessing-enabled':
        this.toggleSettingDetails('preprocessing-details', value);
        break;
      case 'text-correction':
        this.toggleSettingDetails('correction-details', value);
        break;
    }
  },

  // 설정 세부사항 토글
  toggleSettingDetails(detailsId, show) {
    const details = document.getElementById(detailsId);
    if (details) {
      details.style.display = show ? 'block' : 'none';
    }
  },

  // 고급 설정 토글
  toggleAdvancedSettings() {
    const toggle = document.getElementById('advanced-toggle');
    const content = document.getElementById('advanced-content');

    if (!toggle || !content) return;

    const isExpanded = content.style.display === 'block';
    content.style.display = isExpanded ? 'none' : 'block';
    toggle.classList.toggle('expanded', !isExpanded);
  },

  // 섹션 표시
  showSection(sectionName) {
    const sections = ['upload', 'progress', 'result', 'error'];

    sections.forEach(section => {
      const element = document.getElementById(`${section}-section`);
      if (element) {
        element.style.display = section === sectionName ? 'block' : 'none';
      }
    });

    this.state.currentSection = sectionName;

    // 섹션별 초기화 작업
    switch (sectionName) {
      case 'upload':
        this.resetUploadState();
        break;
      case 'progress':
        this.initializeProgress();
        break;
      case 'result':
        this.initializeResult();
        break;
    }
  },

  // 업로드 상태 초기화
  resetUploadState() {
    this.state.uploadedFile = null;
    this.state.processId = null;
    this.state.isProcessing = false;

    // UI 초기화
    const fileInput = document.getElementById('file-input');
    const uploadMessage = document.getElementById('upload-message');
    const fileInfo = document.getElementById('file-info');
    const processButton = document.getElementById('process-button');

    if (fileInput) fileInput.value = '';
    if (uploadMessage) uploadMessage.style.display = 'block';
    if (fileInfo) fileInfo.style.display = 'none';
    if (processButton) processButton.disabled = true;

    // 업로드 영역 클래스 초기화
    const uploadZone = document.getElementById('upload-zone');
    if (uploadZone) {
      uploadZone.classList.remove('has-file', 'drag-over');
    }
  },

  // 처리 재시도
  retryProcessing() {
    if (this.state.uploadedFile) {
      this.startProcessing();
    } else {
      this.showSection('upload');
    }
  },

  // 처리 시작
  async startProcessing() {
    if (!this.state.uploadedFile) {
      this.showToast('파일을 먼저 선택해주세요.', 'warning');
      return;
    }

    try {
      this.state.isProcessing = true;
      this.showSection('progress');

      // 처리 요청 전송
      const response = await this.sendProcessingRequest();

      if (response.ok) {
        const result = await response.json();
        this.state.processId = result.process_id;

        // 진행률 폴링 시작
        this.startProgressPolling();

        this.showToast('문서 처리가 시작되었습니다.', 'success');
      } else {
        throw new Error(`처리 요청 실패: ${response.status}`);
      }
    } catch (error) {
      console.error('처리 시작 오류:', error);
      this.showError('처리를 시작할 수 없습니다. 다시 시도해주세요.');
    }
  },

  // 처리 요청 전송
  async sendProcessingRequest() {
    const formData = new FormData();
    formData.append('file', this.state.uploadedFile);

    const requestData = {
      preprocessing_options: {
        apply_clahe: this.state.settings.preprocessing.clahe,
        deskew_enabled: this.state.settings.preprocessing.deskew,
        noise_removal: this.state.settings.preprocessing.noiseRemoval,
        adaptive_threshold: true
      },
      ocr_engine: this.state.settings.ocrEngine,
      correction_enabled: this.state.settings.textCorrection.enabled,
      correction_options: {
        spacing_correction: this.state.settings.textCorrection.spacing,
        spelling_correction: this.state.settings.textCorrection.spelling,
        custom_rules: false
      }
    };

    return fetch(`${this.config.apiBaseUrl}/process/${this.state.uploadId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData)
    });
  },

  // 처리 취소
  async cancelProcessing() {
    if (!this.state.processId) return;

    try {
      const response = await fetch(`${this.config.apiBaseUrl}/process/${this.state.processId}/cancel`, {
        method: 'DELETE'
      });

      if (response.ok) {
        this.state.isProcessing = false;
        this.showToast('처리가 취소되었습니다.', 'info');
        this.showSection('upload');
      } else {
        throw new Error('취소 요청 실패');
      }
    } catch (error) {
      console.error('취소 오류:', error);
      this.showToast('처리 취소에 실패했습니다.', 'error');
    }
  },

  // 텍스트 복사
  async copyTextToClipboard() {
    const previewContent = document.getElementById('preview-content');
    if (!previewContent) return;

    try {
      await navigator.clipboard.writeText(previewContent.textContent);
      this.showToast('텍스트가 클립보드에 복사되었습니다.', 'success');
    } catch (error) {
      console.error('클립보드 복사 오류:', error);
      this.showToast('클립보드 복사에 실패했습니다.', 'error');
    }
  },

  // 결과 공유
  shareResult() {
    if (navigator.share) {
      navigator.share({
        title: 'K-OCR 처리 결과',
        text: '문서가 성공적으로 처리되었습니다.',
        url: window.location.href
      }).catch(console.error);
    } else {
      // 브라우저가 Web Share API를 지원하지 않는 경우
      this.copyUrlToClipboard();
    }
  },

  // URL 복사
  async copyUrlToClipboard() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      this.showToast('링크가 클립보드에 복사되었습니다.', 'success');
    } catch (error) {
      console.error('URL 복사 오류:', error);
      this.showToast('링크 복사에 실패했습니다.', 'error');
    }
  },

  // 텍스트 미리보기 토글
  toggleTextPreview() {
    const content = document.getElementById('preview-content');
    const toggle = document.getElementById('preview-toggle');

    if (!content || !toggle) return;

    const isExpanded = content.classList.contains('expanded');

    content.classList.toggle('expanded', !isExpanded);
    toggle.classList.toggle('expanded', !isExpanded);

    const toggleText = toggle.querySelector('span');
    if (toggleText) {
      toggleText.textContent = isExpanded ? '전체 보기' : '접기';
    }
  },

  // 오류 표시
  showError(message, details = null) {
    this.showSection('error');

    const errorMessage = document.getElementById('error-message');
    const errorDetails = document.getElementById('error-technical-details');

    if (errorMessage) {
      errorMessage.textContent = message;
    }

    if (errorDetails && details) {
      errorDetails.textContent = details;
    }

    this.state.isProcessing = false;
  },

  // 토스트 알림 표시
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const iconMap = {
      success: 'fas fa-check-circle',
      error: 'fas fa-exclamation-circle',
      warning: 'fas fa-exclamation-triangle',
      info: 'fas fa-info-circle'
    };

    toast.innerHTML = `
      <div class="toast-content">
        <div class="toast-icon">
          <i class="${iconMap[type] || iconMap.info}"></i>
        </div>
        <div class="toast-message">${message}</div>
        <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;

    container.appendChild(toast);

    // 자동 제거 (5초 후)
    setTimeout(() => {
      if (toast.parentElement) {
        toast.remove();
      }
    }, 5000);
  },

  // 툴팁 설정
  setupTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    const tooltip = document.getElementById('tooltip');

    if (!tooltip) return;

    tooltipElements.forEach(element => {
      element.addEventListener('mouseenter', (e) => {
        const text = e.target.getAttribute('data-tooltip');
        tooltip.textContent = text;
        tooltip.classList.add('show');

        // 위치 설정
        const rect = e.target.getBoundingClientRect();
        tooltip.style.left = `${rect.left + rect.width / 2}px`;
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
      });

      element.addEventListener('mouseleave', () => {
        tooltip.classList.remove('show');
      });
    });
  },

  // 키보드 단축키
  handleKeyboardShortcuts(event) {
    if (event.ctrlKey || event.metaKey) {
      switch (event.key) {
        case 'Enter':
          if (this.state.currentSection === 'upload' && !event.target.matches('button')) {
            const processButton = document.getElementById('process-button');
            if (processButton && !processButton.disabled) {
              processButton.click();
            }
          }
          break;
        case 'c':
          if (this.state.currentSection === 'result') {
            event.preventDefault();
            this.copyTextToClipboard();
          }
          break;
      }
    }

    if (event.key === 'Escape') {
      if (this.state.isProcessing) {
        this.cancelProcessing();
      }
    }
  },

  // 페이지 이탈 확인
  handlePageUnload(event) {
    if (this.state.isProcessing) {
      const message = '문서 처리가 진행 중입니다. 페이지를 떠나시겠습니까?';
      event.returnValue = message;
      return message;
    }
  },

  // 설정 로드
  loadSettings() {
    const saved = localStorage.getItem('ocr-settings');
    if (saved) {
      try {
        const settings = JSON.parse(saved);
        this.state.settings = { ...this.state.settings, ...settings };
        this.applySettingsToUI();
      } catch (error) {
        console.error('설정 로드 오류:', error);
      }
    }
  },

  // 설정 저장
  saveSettings() {
    try {
      localStorage.setItem('ocr-settings', JSON.stringify(this.state.settings));
    } catch (error) {
      console.error('설정 저장 오류:', error);
    }
  },

  // UI에 설정 적용
  applySettingsToUI() {
    const settingElements = {
      'preprocessing-enabled': this.state.settings.preprocessing.enabled,
      'clahe-enabled': this.state.settings.preprocessing.clahe,
      'deskew-enabled': this.state.settings.preprocessing.deskew,
      'noise-removal': this.state.settings.preprocessing.noiseRemoval,
      'ocr-engine': this.state.settings.ocrEngine,
      'text-correction': this.state.settings.textCorrection.enabled,
      'spacing-correction': this.state.settings.textCorrection.spacing,
      'spelling-correction': this.state.settings.textCorrection.spelling,
      'dpi-setting': this.state.settings.advanced.dpi,
      'language-model': this.state.settings.advanced.language
    };

    Object.entries(settingElements).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) {
        if (element.type === 'checkbox') {
          element.checked = value;
        } else {
          element.value = value;
        }
      }
    });

    // 의존 설정들 업데이트
    this.toggleSettingDetails('preprocessing-details', this.state.settings.preprocessing.enabled);
    this.toggleSettingDetails('correction-details', this.state.settings.textCorrection.enabled);
  },

  // 브라우저 지원 확인
  checkBrowserSupport() {
    const features = {
      'File API': window.File && window.FileReader && window.FileList && window.Blob,
      'Drag and Drop': 'ondrag' in document.createElement('div'),
      'FormData': window.FormData,
      'Fetch API': window.fetch,
      'Clipboard API': navigator.clipboard
    };

    const unsupported = Object.entries(features)
      .filter(([name, supported]) => !supported)
      .map(([name]) => name);

    if (unsupported.length > 0) {
      console.warn('지원되지 않는 기능들:', unsupported);
      this.showToast(`일부 기능이 이 브라우저에서 지원되지 않습니다: ${unsupported.join(', ')}`, 'warning');
    }
  },

  // 파일 크기 포맷
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // 시간 포맷 (초를 분:초로)
  formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  },

  // 디바운스 유틸리티
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
};

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  window.OCRApp.init();
});

// 전역 오류 처리
window.addEventListener('error', (event) => {
  console.error('전역 오류:', event.error);
  if (window.OCRApp) {
    window.OCRApp.showToast('예상치 못한 오류가 발생했습니다.', 'error');
  }
});

// 네트워크 상태 감지
window.addEventListener('online', () => {
  if (window.OCRApp) {
    window.OCRApp.showToast('네트워크 연결이 복구되었습니다.', 'success');
  }
});

window.addEventListener('offline', () => {
  if (window.OCRApp) {
    window.OCRApp.showToast('네트워크 연결이 끊어졌습니다.', 'warning');
  }
});