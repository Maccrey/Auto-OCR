/**
 * K-OCR Web Corrector - Upload JavaScript
 * 파일 업로드 및 드래그 앤 드롭 기능
 */

window.OCRApp.Upload = {
  // 초기화
  init() {
    console.log('Upload 모듈 초기화 중...');

    this.setupFileInput();
    this.setupDragAndDrop();
    this.setupUploadButton();
    this.setupProcessButton();
    this.setupRemoveButton();

    console.log('Upload 모듈 초기화 완료');
  },

  // 파일 입력 설정
  setupFileInput() {
    const fileInput = document.getElementById('file-input');
    if (!fileInput) return;

    fileInput.addEventListener('change', this.handleFileSelect.bind(this));
  },

  // 드래그 앤 드롭 설정
  setupDragAndDrop() {
    const uploadZone = document.getElementById('upload-zone');
    if (!uploadZone) return;

    // 기본 드래그 이벤트 방지
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      uploadZone.addEventListener(eventName, this.preventDefaults, false);
      document.body.addEventListener(eventName, this.preventDefaults, false);
    });

    // 드래그 스타일 추가/제거
    ['dragenter', 'dragover'].forEach(eventName => {
      uploadZone.addEventListener(eventName, this.handleDragEnter.bind(this), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      uploadZone.addEventListener(eventName, this.handleDragLeave.bind(this), false);
    });

    // 드롭 처리
    uploadZone.addEventListener('drop', this.handleDrop.bind(this), false);
  },

  // 업로드 버튼 설정
  setupUploadButton() {
    const uploadButton = document.getElementById('upload-button');
    const fileInput = document.getElementById('file-input');

    if (!uploadButton || !fileInput) return;

    uploadButton.addEventListener('click', () => {
      fileInput.click();
    });
  },

  // 처리 버튼 설정
  setupProcessButton() {
    const processButton = document.getElementById('process-button');
    if (!processButton) return;

    processButton.addEventListener('click', this.handleProcessClick.bind(this));
  },

  // 파일 제거 버튼 설정
  setupRemoveButton() {
    const removeButton = document.getElementById('remove-file');
    if (!removeButton) return;

    removeButton.addEventListener('click', this.removeFile.bind(this));
  },

  // 기본 이벤트 방지
  preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  },

  // 드래그 진입
  handleDragEnter(e) {
    const uploadZone = document.getElementById('upload-zone');
    if (uploadZone) {
      uploadZone.classList.add('drag-over');
    }
  },

  // 드래그 떠남
  handleDragLeave(e) {
    // 실제로 떠났는지 확인 (자식 요소로 이동한 경우 제외)
    const uploadZone = document.getElementById('upload-zone');
    if (!uploadZone) return;

    if (!uploadZone.contains(e.relatedTarget)) {
      uploadZone.classList.remove('drag-over');
    }
  },

  // 드롭 처리
  handleDrop(e) {
    const uploadZone = document.getElementById('upload-zone');
    if (uploadZone) {
      uploadZone.classList.remove('drag-over');
    }

    const files = e.dataTransfer.files;
    this.handleFiles(files);
  },

  // 파일 선택 처리
  handleFileSelect(e) {
    const files = e.target.files;
    this.handleFiles(files);
  },

  // 파일 처리
  handleFiles(files) {
    if (files.length === 0) return;

    const file = files[0];

    // 파일 검증
    if (!this.validateFile(file)) {
      return;
    }

    // 파일 정보 표시
    this.displayFileInfo(file);

    // 상태 업데이트
    window.OCRApp.state.uploadedFile = file;

    // 처리 버튼 활성화
    this.enableProcessButton();

    // 파일 업로드 시작
    this.uploadFile(file);
  },

  // 파일 검증
  validateFile(file) {
    // 파일 존재 확인
    if (!file) {
      window.OCRApp.showToast('파일이 선택되지 않았습니다.', 'warning');
      return false;
    }

    // 파일 크기 확인
    if (file.size > window.OCRApp.config.maxFileSize) {
      const maxSizeMB = window.OCRApp.config.maxFileSize / (1024 * 1024);
      window.OCRApp.showToast(`파일 크기가 너무 큽니다. 최대 ${maxSizeMB}MB까지 지원됩니다.`, 'error');
      return false;
    }

    // 파일 형식 확인
    const fileName = file.name.toLowerCase();
    const isValidFormat = window.OCRApp.config.supportedFormats.some(format =>
      fileName.endsWith(format)
    );

    if (!isValidFormat) {
      const formats = window.OCRApp.config.supportedFormats.join(', ');
      window.OCRApp.showToast(`지원되지 않는 파일 형식입니다. 지원 형식: ${formats}`, 'error');
      return false;
    }

    // MIME 타입 확인 (추가 보안)
    if (file.type && !file.type.includes('pdf')) {
      window.OCRApp.showToast('PDF 파일만 업로드할 수 있습니다.', 'error');
      return false;
    }

    return true;
  },

  // 파일 정보 표시
  displayFileInfo(file) {
    const uploadMessage = document.getElementById('upload-message');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const filePages = document.getElementById('file-pages');
    const uploadZone = document.getElementById('upload-zone');

    // UI 업데이트
    if (uploadMessage) uploadMessage.style.display = 'none';
    if (fileInfo) fileInfo.style.display = 'flex';
    if (uploadZone) uploadZone.classList.add('has-file');

    // 파일 정보 설정
    if (fileName) fileName.textContent = file.name;
    if (fileSize) fileSize.textContent = `크기: ${window.OCRApp.formatFileSize(file.size)}`;

    // 페이지 수는 업로드 후에 설정
    if (filePages) filePages.textContent = '페이지 수: 확인 중...';

    window.OCRApp.showToast('파일이 선택되었습니다.', 'success');
  },

  // 파일 업로드
  async uploadFile(file) {
    const uploadProgress = document.getElementById('upload-progress');
    const uploadProgressFill = document.getElementById('upload-progress-fill');
    const uploadStatus = document.getElementById('upload-status');

    try {
      // 진행률 표시 시작
      if (uploadProgress) uploadProgress.style.display = 'block';

      const formData = new FormData();
      formData.append('file', file);

      // XMLHttpRequest를 사용하여 업로드 진행률 추적
      const uploadPromise = new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        // 진행률 이벤트
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;

            if (uploadProgressFill) {
              uploadProgressFill.style.width = `${percentComplete}%`;
            }

            if (uploadStatus) {
              uploadStatus.textContent = `업로드 중... ${Math.round(percentComplete)}%`;
            }
          }
        });

        // 완료 이벤트
        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(`업로드 실패: ${xhr.status}`));
          }
        });

        // 오류 이벤트
        xhr.addEventListener('error', () => {
          reject(new Error('네트워크 오류가 발생했습니다.'));
        });

        // 요청 전송
        xhr.open('POST', `${window.OCRApp.config.apiBaseUrl}/upload`);
        xhr.send(formData);
      });

      // 업로드 완료 대기
      const result = await uploadPromise;

      // 결과 처리
      window.OCRApp.state.uploadId = result.upload_id;

      // 페이지 수 업데이트
      this.updateFilePages(result);

      // 진행률 숨김
      if (uploadProgress) {
        setTimeout(() => {
          uploadProgress.style.display = 'none';
        }, 1000);
      }

      window.OCRApp.showToast('파일 업로드가 완료되었습니다.', 'success');

    } catch (error) {
      console.error('업로드 오류:', error);

      // 진행률 숨김
      if (uploadProgress) uploadProgress.style.display = 'none';

      // 오류 표시
      window.OCRApp.showToast(error.message || '파일 업로드에 실패했습니다.', 'error');

      // 파일 정보 초기화
      this.removeFile();
    }
  },

  // 파일 페이지 수 업데이트
  updateFilePages(uploadResult) {
    const filePages = document.getElementById('file-pages');

    if (filePages && uploadResult.pages) {
      filePages.textContent = `페이지 수: ${uploadResult.pages}페이지`;
    } else if (filePages) {
      // 페이지 정보가 없는 경우 기본값
      filePages.textContent = '페이지 수: 확인됨';
    }
  },

  // 파일 제거
  removeFile() {
    const uploadMessage = document.getElementById('upload-message');
    const fileInfo = document.getElementById('file-info');
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const uploadProgress = document.getElementById('upload-progress');

    // UI 초기화
    if (uploadMessage) uploadMessage.style.display = 'block';
    if (fileInfo) fileInfo.style.display = 'none';
    if (uploadZone) uploadZone.classList.remove('has-file');
    if (fileInput) fileInput.value = '';
    if (uploadProgress) uploadProgress.style.display = 'none';

    // 상태 초기화
    window.OCRApp.state.uploadedFile = null;
    window.OCRApp.state.uploadId = null;

    // 처리 버튼 비활성화
    this.disableProcessButton();

    window.OCRApp.showToast('파일이 제거되었습니다.', 'info');
  },

  // 처리 버튼 활성화
  enableProcessButton() {
    const processButton = document.getElementById('process-button');
    if (processButton) {
      processButton.disabled = false;
    }
  },

  // 처리 버튼 비활성화
  disableProcessButton() {
    const processButton = document.getElementById('process-button');
    if (processButton) {
      processButton.disabled = true;
    }
  },

  // 처리 버튼 클릭 처리
  handleProcessClick(e) {
    e.preventDefault();

    if (!window.OCRApp.state.uploadedFile) {
      window.OCRApp.showToast('먼저 파일을 선택해주세요.', 'warning');
      return;
    }

    if (!window.OCRApp.state.uploadId) {
      window.OCRApp.showToast('파일 업로드가 완료되지 않았습니다. 잠시 후 다시 시도해주세요.', 'warning');
      return;
    }

    // 설정 검증
    if (!this.validateSettings()) {
      return;
    }

    // 처리 시작
    window.OCRApp.startProcessing();
  },

  // 설정 검증
  validateSettings() {
    // OCR 엔진 확인
    const ocrEngine = window.OCRApp.state.settings.ocrEngine;
    if (!ocrEngine) {
      window.OCRApp.showToast('OCR 엔진을 선택해주세요.', 'warning');
      return false;
    }

    // 파일 크기가 큰 경우 경고
    const file = window.OCRApp.state.uploadedFile;
    const largeSizeThreshold = 20 * 1024 * 1024; // 20MB

    if (file && file.size > largeSizeThreshold) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      const confirmed = confirm(
        `파일 크기가 큽니다 (${sizeMB}MB). 처리 시간이 오래 걸릴 수 있습니다. 계속하시겠습니까?`
      );

      if (!confirmed) {
        return false;
      }
    }

    return true;
  },

  // 파일 검증 (고급)
  async validateFileContent(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = function(e) {
        const arrayBuffer = e.target.result;
        const bytes = new Uint8Array(arrayBuffer.slice(0, 4));

        // PDF 파일 시그니처 확인 (%PDF)
        const pdfSignature = [0x25, 0x50, 0x44, 0x46]; // %PDF
        const isValidPDF = bytes.every((byte, index) => byte === pdfSignature[index]);

        if (isValidPDF) {
          resolve(true);
        } else {
          reject(new Error('유효하지 않은 PDF 파일입니다.'));
        }
      };

      reader.onerror = () => reject(new Error('파일을 읽을 수 없습니다.'));
      reader.readAsArrayBuffer(file.slice(0, 4));
    });
  },

  // 업로드 상태 확인
  async checkUploadStatus(uploadId) {
    try {
      const response = await fetch(`${window.OCRApp.config.apiBaseUrl}/upload/${uploadId}/status`);

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error(`상태 확인 실패: ${response.status}`);
      }
    } catch (error) {
      console.error('업로드 상태 확인 오류:', error);
      return null;
    }
  }
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  if (window.OCRApp && window.OCRApp.Upload) {
    window.OCRApp.Upload.init();
  }
});

// 브라우저 뒤로가기 시 파일 상태 복원 방지
window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
    // 페이지가 캐시에서 복원된 경우 파일 상태 초기화
    if (window.OCRApp && window.OCRApp.Upload) {
      window.OCRApp.Upload.removeFile();
    }
  }
});