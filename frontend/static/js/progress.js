/**
 * K-OCR Web Corrector - Progress JavaScript
 * 처리 진행률 및 결과 표시 기능
 */

window.OCRApp.Progress = {
  // 초기화
  init() {
    console.log('Progress 모듈 초기화 중...');

    this.setupProgressEvents();
    this.setupResultEvents();

    console.log('Progress 모듈 초기화 완료');
  },

  // 진행률 이벤트 설정
  setupProgressEvents() {
    // 새 파일 선택 시 이벤트 리스너
    document.addEventListener('newFileSelected', this.resetProgress.bind(this));

    // 처리 시작 이벤트 리스너
    document.addEventListener('processingStarted', this.startProgressTracking.bind(this));
  },

  // 결과 이벤트 설정
  setupResultEvents() {
    const downloadButton = document.getElementById('download-button');
    const restartButton = document.getElementById('restart-button');
    const copyButton = document.getElementById('copy-result');

    if (downloadButton) {
      downloadButton.addEventListener('click', this.handleDownload.bind(this));
    }

    if (restartButton) {
      restartButton.addEventListener('click', this.handleRestart.bind(this));
    }

    if (copyButton) {
      copyButton.addEventListener('click', this.handleCopyResult.bind(this));
    }
  },

  // 진행률 초기화
  resetProgress() {
    const progressSection = document.getElementById('progress-section');
    const resultSection = document.getElementById('result-section');
    const errorSection = document.getElementById('error-section');

    // 모든 섹션 숨김
    if (progressSection) progressSection.style.display = 'none';
    if (resultSection) resultSection.style.display = 'none';
    if (errorSection) errorSection.style.display = 'none';

    // 진행률 초기화
    this.updateProgress(0, '대기 중...');

    // 폴링 중단
    this.stopProgressPolling();
  },

  // 진행률 추적 시작
  async startProgressTracking(event) {
    const processId = event.detail.processId;

    if (!processId) {
      console.error('Process ID가 없습니다.');
      return;
    }

    window.OCRApp.state.processId = processId;

    // 진행률 섹션 표시
    this.showProgressSection();

    // 진행률 폴링 시작
    this.startProgressPolling(processId);
  },

  // 진행률 섹션 표시
  showProgressSection() {
    const uploadSection = document.getElementById('upload-section');
    const progressSection = document.getElementById('progress-section');

    if (uploadSection) uploadSection.style.display = 'none';
    if (progressSection) progressSection.style.display = 'block';

    // 애니메이션 효과
    if (progressSection) {
      progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  },

  // 진행률 폴링 시작
  startProgressPolling(processId) {
    console.log('진행률 폴링 시작:', processId);

    // 기존 폴링 중단
    this.stopProgressPolling();

    // 즉시 첫 번째 상태 확인
    this.checkProcessingStatus(processId);

    // 정기적인 폴링 시작 (2초 간격)
    this.pollingInterval = setInterval(() => {
      this.checkProcessingStatus(processId);
    }, 2000);
  },

  // 진행률 폴링 중단
  stopProgressPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
      console.log('진행률 폴링 중단');
    }
  },

  // 처리 상태 확인
  async checkProcessingStatus(processId) {
    try {
      const response = await fetch(`${window.OCRApp.config.apiBaseUrl}/process/${processId}/status`);

      if (!response.ok) {
        throw new Error(`상태 확인 실패: ${response.status}`);
      }

      const data = await response.json();

      // 상태에 따른 처리
      switch (data.status) {
        case 'pending':
          this.updateProgress(5, '처리 대기 중...');
          break;
        case 'converting':
          this.updateProgress(20, 'PDF를 이미지로 변환 중...');
          break;
        case 'preprocessing':
          this.updateProgress(40, '이미지 전처리 중...');
          break;
        case 'ocr':
          this.updateProgress(70, 'OCR 텍스트 인식 중...');
          break;
        case 'correcting':
          this.updateProgress(90, '텍스트 교정 중...');
          break;
        case 'completed':
          this.updateProgress(100, '처리 완료!');
          this.stopProgressPolling();
          await this.handleProcessingComplete(processId);
          break;
        case 'failed':
          this.stopProgressPolling();
          this.handleProcessingError(data.error || '처리 중 오류가 발생했습니다.');
          break;
        default:
          console.warn('알 수 없는 상태:', data.status);
      }

      // 예상 시간 업데이트
      if (data.estimated_time) {
        this.updateEstimatedTime(data.estimated_time);
      }

    } catch (error) {
      console.error('상태 확인 오류:', error);

      // 연결 오류 횟수 카운트
      this.connectionErrors = (this.connectionErrors || 0) + 1;

      // 3회 연속 오류 시 폴링 중단
      if (this.connectionErrors >= 3) {
        this.stopProgressPolling();
        this.handleProcessingError('서버 연결에 실패했습니다. 페이지를 새로고침해주세요.');
      }
    }
  },

  // 진행률 업데이트
  updateProgress(percentage, message) {
    const progressBar = document.getElementById('progress-bar-fill');
    const progressText = document.getElementById('progress-text');
    const currentStep = document.getElementById('current-step');

    if (progressBar) {
      progressBar.style.width = `${percentage}%`;

      // 애니메이션 효과
      progressBar.style.transition = 'width 0.5s ease-in-out';
    }

    if (progressText) {
      progressText.textContent = `${percentage}%`;
    }

    if (currentStep) {
      currentStep.textContent = message;
    }

    // 진행 단계별 아이콘 업데이트
    this.updateStepIcons(percentage);

    // 상태 저장
    window.OCRApp.state.currentProgress = {
      percentage: percentage,
      message: message
    };
  },

  // 단계별 아이콘 업데이트
  updateStepIcons(percentage) {
    const steps = [
      { id: 'step-upload', threshold: 0 },
      { id: 'step-convert', threshold: 20 },
      { id: 'step-preprocess', threshold: 40 },
      { id: 'step-ocr', threshold: 70 },
      { id: 'step-correct', threshold: 90 },
      { id: 'step-complete', threshold: 100 }
    ];

    steps.forEach(step => {
      const element = document.getElementById(step.id);
      if (element) {
        if (percentage >= step.threshold) {
          element.classList.add('completed');
          element.classList.remove('current');
        } else if (percentage >= step.threshold - 20) {
          element.classList.add('current');
          element.classList.remove('completed');
        } else {
          element.classList.remove('completed', 'current');
        }
      }
    });
  },

  // 예상 시간 업데이트
  updateEstimatedTime(estimatedSeconds) {
    const estimatedTimeElement = document.getElementById('estimated-time');

    if (estimatedTimeElement && estimatedSeconds > 0) {
      const minutes = Math.floor(estimatedSeconds / 60);
      const seconds = estimatedSeconds % 60;

      let timeText = '';
      if (minutes > 0) {
        timeText = `약 ${minutes}분 ${seconds}초 남음`;
      } else {
        timeText = `약 ${seconds}초 남음`;
      }

      estimatedTimeElement.textContent = timeText;
      estimatedTimeElement.style.display = 'block';
    }
  },

  // 처리 완료 처리
  async handleProcessingComplete(processId) {
    try {
      // 결과 데이터 가져오기
      const response = await fetch(`${window.OCRApp.config.apiBaseUrl}/process/${processId}/result`);

      if (!response.ok) {
        throw new Error(`결과 가져오기 실패: ${response.status}`);
      }

      const result = await response.json();

      // 결과 표시
      this.showResult(result);

      window.OCRApp.showToast('문서 처리가 완료되었습니다!', 'success');

    } catch (error) {
      console.error('결과 가져오기 오류:', error);
      this.handleProcessingError('결과를 가져오는데 실패했습니다.');
    }
  },

  // 결과 표시
  showResult(result) {
    const progressSection = document.getElementById('progress-section');
    const resultSection = document.getElementById('result-section');
    const resultText = document.getElementById('result-text');
    const resultStats = document.getElementById('result-stats');
    const downloadButton = document.getElementById('download-button');

    // 섹션 전환
    if (progressSection) progressSection.style.display = 'none';
    if (resultSection) resultSection.style.display = 'block';

    // 결과 텍스트 표시
    if (resultText && result.text) {
      resultText.textContent = result.text;
    }

    // 통계 정보 표시
    if (resultStats && result.stats) {
      const stats = result.stats;
      resultStats.innerHTML = `
        <div class="stat-item">
          <span class="stat-label">총 글자 수:</span>
          <span class="stat-value">${stats.total_characters || 0}자</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">처리 시간:</span>
          <span class="stat-value">${stats.processing_time || 0}초</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">페이지 수:</span>
          <span class="stat-value">${stats.page_count || 0}페이지</span>
        </div>
      `;
    }

    // 다운로드 버튼 설정
    if (downloadButton && result.download_url) {
      downloadButton.href = result.download_url;
      downloadButton.style.display = 'inline-flex';
    }

    // 결과 상태 저장
    window.OCRApp.state.result = result;

    // 스크롤 이동
    if (resultSection) {
      resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  },

  // 처리 오류 처리
  handleProcessingError(errorMessage) {
    const progressSection = document.getElementById('progress-section');
    const errorSection = document.getElementById('error-section');
    const errorMessage_element = document.getElementById('error-message');

    // 섹션 전환
    if (progressSection) progressSection.style.display = 'none';
    if (errorSection) errorSection.style.display = 'block';

    // 오류 메시지 표시
    if (errorMessage_element) {
      errorMessage_element.textContent = errorMessage;
    }

    // 토스트 메시지
    window.OCRApp.showToast(errorMessage, 'error');

    // 스크롤 이동
    if (errorSection) {
      errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 상태 초기화
    window.OCRApp.state.processId = null;
    window.OCRApp.state.currentProgress = null;
  },

  // 다운로드 처리
  async handleDownload(e) {
    e.preventDefault();

    const result = window.OCRApp.state.result;

    if (!result || !result.download_url) {
      window.OCRApp.showToast('다운로드할 파일이 없습니다.', 'error');
      return;
    }

    try {
      // 다운로드 링크 클릭
      const link = document.createElement('a');
      link.href = result.download_url;
      link.download = result.filename || 'ocr_result.txt';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      window.OCRApp.showToast('파일 다운로드를 시작합니다.', 'success');

    } catch (error) {
      console.error('다운로드 오류:', error);
      window.OCRApp.showToast('파일 다운로드에 실패했습니다.', 'error');
    }
  },

  // 결과 복사
  async handleCopyResult(e) {
    e.preventDefault();

    const result = window.OCRApp.state.result;

    if (!result || !result.text) {
      window.OCRApp.showToast('복사할 텍스트가 없습니다.', 'warning');
      return;
    }

    try {
      await navigator.clipboard.writeText(result.text);
      window.OCRApp.showToast('텍스트가 클립보드에 복사되었습니다.', 'success');

    } catch (error) {
      console.error('클립보드 복사 오류:', error);

      // 대체 방법: 텍스트 선택
      this.selectResultText();
      window.OCRApp.showToast('텍스트를 선택했습니다. Ctrl+C로 복사하세요.', 'info');
    }
  },

  // 결과 텍스트 선택
  selectResultText() {
    const resultText = document.getElementById('result-text');

    if (resultText) {
      const range = document.createRange();
      range.selectNodeContents(resultText);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
    }
  },

  // 재시작 처리
  handleRestart(e) {
    e.preventDefault();

    // 모든 상태 초기화
    this.resetProgress();
    window.OCRApp.state.result = null;
    window.OCRApp.state.processId = null;

    // 업로드 섹션으로 돌아가기
    window.OCRApp.showSection('upload');

    window.OCRApp.showToast('새 파일을 선택해주세요.', 'info');
  },

  // 진행률 상태 복원
  restoreProgressState() {
    const processId = window.OCRApp.state.processId;

    if (processId) {
      console.log('진행률 상태 복원:', processId);
      this.showProgressSection();
      this.startProgressPolling(processId);
    }
  },

  // 키보드 단축키 처리
  handleKeyboardShortcuts(e) {
    // 결과 화면에서만 동작
    if (window.OCRApp.state.currentSection !== 'result') {
      return;
    }

    switch (e.key) {
      case 'c':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          this.handleCopyResult(e);
        }
        break;
      case 'd':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          this.handleDownload(e);
        }
        break;
      case 'r':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          this.handleRestart(e);
        }
        break;
    }
  }
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  if (window.OCRApp && window.OCRApp.Progress) {
    window.OCRApp.Progress.init();

    // 키보드 단축키 등록
    document.addEventListener('keydown', window.OCRApp.Progress.handleKeyboardShortcuts.bind(window.OCRApp.Progress));

    // 페이지 새로고침 시 상태 복원
    window.OCRApp.Progress.restoreProgressState();
  }
});

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', () => {
  if (window.OCRApp && window.OCRApp.Progress) {
    window.OCRApp.Progress.stopProgressPolling();
  }
});