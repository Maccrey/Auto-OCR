# K-OCR Web Corrector - Claude 개발 가이드

## 1. 프로젝트 개요

### 프로젝트 명
K-OCR Web Corrector - 한국어 문서 OCR 및 교정 웹 서비스

### 목적
PDF 문서를 웹을 통해 업로드하여 PNG로 변환 후, 이미지 전처리 및 OCR 처리를 거쳐 한국어 텍스트 파일로 다운로드할 수 있는 웹 애플리케이션 개발

### 핵심 워크플로우
1. 사용자가 PDF 파일을 웹 인터페이스를 통해 업로드
2. 서버에서 PDF를 PNG 이미지로 변환
3. 이미지 전처리 (흑백변환, 대비조정, 기울기보정, 노이즈제거 등)
4. OCR 엔진을 통한 한국어 텍스트 인식
5. 텍스트 교정 (띄어쓰기, 맞춤법)
6. 최종 텍스트 파일을 다운로드 형태로 제공

### 기술적 특징
- **웹 기반**: 브라우저만으로 접근 가능한 웹 서비스
- **비동기 처리**: Celery와 Redis를 활용한 백그라운드 작업 처리
- **실시간 피드백**: 처리 진행률 실시간 표시
- **확장성**: Docker 컨테이너 기반 배포 및 클라우드 확장 가능

## 2. 개발 명령어

### 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 설정값 입력
```

### 개발 서버 실행
```bash
# FastAPI 개발 서버 실행
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Redis 서버 실행 (별도 터미널)
redis-server

# Celery worker 실행 (별도 터미널)
celery -A backend.core.tasks worker --loglevel=info
```

### 테스트 실행
```bash
# 전체 테스트 실행
pytest

# 커버리지와 함께 테스트 실행
pytest --cov=backend --cov-report=html

# 특정 모듈 테스트
pytest tests/test_core/

# API 테스트만 실행
pytest tests/test_api/
```

### 코드 품질 검사
```bash
# 코드 포맷팅
black backend/ tests/

# 린트 검사
flake8 backend/ tests/

# 타입 체킹
mypy backend/
```

### Docker 명령어
```bash
# 개발 환경 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 컨테이너 정지
docker-compose down

# 프로덕션 빌드
docker build -t k-ocr-web .
```

## 3. 아키텍처 구조

### 전체 시스템 아키텍처
```
┌─────────────────────────┐
│     Frontend Layer      │
│  (HTML/CSS/JavaScript)  │
│   - File Upload UI      │
│   - Progress Display    │
│   - Settings Panel      │
│   - Download Interface  │
└─────────────────────────┘
            │
            ▼ HTTP/HTTPS
┌─────────────────────────┐
│    Backend API Layer    │
│      (FastAPI)          │
│   - Upload Endpoints    │
│   - Processing Status   │
│   - Download Endpoints  │
└─────────────────────────┘
            │
            ▼ Task Queue
┌─────────────────────────┐
│   Background Workers    │
│    (Celery + Redis)     │
│   - PDF Conversion      │
│   - Image Processing    │
│   - OCR Processing      │
│   - Text Correction     │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│   Business Logic        │
│   - PDFConverter        │
│   - ImageProcessor      │
│   - OCREngine          │
│   - TextCorrector      │
│   - FileGenerator      │
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│     Data Layer         │
│   - TempStorage        │
│   - ConfigManager      │
│   - File System        │
└─────────────────────────┘
```

### 디렉토리 구조
```
k_ocr_web_corrector/
├── backend/
│   ├── api/                    # FastAPI 라우터들
│   │   ├── upload.py          # 파일 업로드 API
│   │   ├── processing.py      # 처리 상태 API
│   │   └── download.py        # 결과 다운로드 API
│   ├── core/                  # 핵심 비즈니스 로직
│   │   ├── pdf_converter.py   # PDF → PNG 변환
│   │   ├── image_processor.py # 이미지 전처리
│   │   ├── ocr_engine.py      # OCR 엔진 관리
│   │   ├── text_corrector.py  # 텍스트 교정
│   │   ├── file_generator.py  # 결과 파일 생성
│   │   └── tasks.py          # Celery 태스크 정의
│   ├── utils/                 # 유틸리티 모듈
│   │   ├── temp_storage.py    # 임시 파일 관리
│   │   ├── config_manager.py  # 설정 관리
│   │   └── file_handler.py    # 파일 처리 유틸
│   └── main.py               # FastAPI 애플리케이션 진입점
├── frontend/
│   ├── static/
│   │   ├── css/              # 스타일시트
│   │   ├── js/               # JavaScript 파일
│   │   └── images/           # 이미지 리소스
│   └── templates/            # Jinja2 템플릿
│       ├── index.html        # 메인 페이지
│       ├── upload.html       # 업로드 페이지
│       └── result.html       # 결과 페이지
├── tests/                    # 테스트 파일들
├── temp_storage/            # 임시 파일 저장소
├── config/                  # 설정 파일들
├── docker-compose.yml       # 개발 환경 Docker 구성
├── Dockerfile              # 프로덕션 이미지 빌드
├── requirements.txt        # Python 의존성
└── .env.example           # 환경변수 예시
```

## 4. 기술적 결정사항

### 웹 프레임워크 선택
- **FastAPI**: 현대적이고 빠른 Python 웹 프레임워크
  - 자동 API 문서 생성 (OpenAPI/Swagger)
  - 비동기 처리 지원
  - 타입 힌트 기반 개발
  - Pydantic을 통한 데이터 검증

### 비동기 작업 처리
- **Celery + Redis**: 백그라운드 작업 처리
  - OCR 처리는 시간이 오래 걸리므로 비동기 처리 필수
  - Redis를 메시지 브로커 및 결과 백엔드로 사용
  - 작업 진행률 추적 및 상태 관리

### OCR 엔진
- **PaddleOCR**: 주요 OCR 엔진
  - 한국어 지원 우수
  - GPU 가속 지원
  - 오픈소스 라이선스
- **Tesseract**: 보조 OCR 엔진
  - 널리 사용되는 오픈소스 OCR
  - 한국어 모델 지원

### 텍스트 교정
- **KoSpacing**: 한국어 띄어쓰기 교정
- **py-hanspell**: 한국어 맞춤법 검사

### 이미지 처리
- **OpenCV**: 이미지 전처리 및 품질 향상
- **Pillow**: 기본 이미지 처리
- **scikit-image**: 고급 이미지 처리 알고리즘

### 컨테이너화
- **Docker**: 개발 및 배포 환경 통일
- **Docker Compose**: 멀티 컨테이너 개발 환경

## 5. 컴포넌트 구성

### Backend 컴포넌트

#### API Layer
```python
# api/upload.py
@router.post("/api/upload")
async def upload_file(file: UploadFile):
    """PDF 파일 업로드 및 검증"""
    
@router.get("/api/upload/{upload_id}/status")
async def get_upload_status(upload_id: str):
    """업로드 상태 확인"""
```

#### Core Modules
```python
# core/pdf_converter.py
class PDFConverter:
    def convert_pdf_to_png(self, pdf_path: str) -> List[str]:
        """PDF를 PNG 이미지들로 변환"""
        
# core/ocr_engine.py
class OCREngine:
    def recognize_text(self, image_path: str) -> OCRResult:
        """이미지에서 텍스트 인식"""
        
# core/text_corrector.py
class TextCorrector:
    def correct_text(self, text: str) -> str:
        """텍스트 교정 (띄어쓰기 + 맞춤법)"""
```

#### Background Tasks
```python
# core/tasks.py
@celery_app.task(bind=True)
def process_document(self, upload_id: str, options: dict):
    """문서 처리 메인 태스크"""
    # 1. PDF → PNG 변환
    # 2. 이미지 전처리
    # 3. OCR 처리
    # 4. 텍스트 교정
    # 5. 결과 파일 생성
```

### Frontend 컴포넌트

#### 파일 업로드 인터페이스
```html
<!-- templates/index.html -->
<div class="upload-area" id="upload-zone">
    <input type="file" id="file-input" accept=".pdf">
    <div class="upload-message">
        PDF 파일을 드래그하거나 클릭하여 업로드
    </div>
</div>
```

#### 진행률 표시
```javascript
// static/js/progress.js
function updateProgress(processId) {
    fetch(`/api/process/${processId}/status`)
        .then(response => response.json())
        .then(data => {
            updateProgressBar(data.progress);
            updateStatusMessage(data.current_step);
        });
}
```

### 데이터 모델
```python
# Pydantic 모델들
class UploadRequest(BaseModel):
    file_id: str
    filename: str
    file_size: int
    upload_time: datetime

class ProcessingStatus(BaseModel):
    process_id: str
    status: str  # 'pending', 'converting', 'ocr', 'completed'
    progress: int  # 0-100
    current_step: str
    estimated_time: Optional[int]

class ProcessingResult(BaseModel):
    process_id: str
    original_filename: str
    final_text: str
    download_url: str
    expires_at: datetime
```

## 6. 중요 참고사항

### 보안 고려사항
1. **파일 업로드 보안**
   - PDF 파일만 허용 (MIME 타입 검증)
   - 파일 크기 제한 (최대 50MB)
   - 업로드 속도 제한 (Rate Limiting)

2. **임시 파일 관리**
   - 업로드된 파일 24시간 후 자동 삭제
   - 처리 완료 후 중간 파일들 즉시 삭제
   - 파일 접근 권한 검증 (업로더만 다운로드 가능)

3. **통신 보안**
   - HTTPS 강제 사용
   - CSRF 토큰 검증
   - XSS 방지를 위한 입력 검증

### 성능 최적화
1. **비동기 처리**
   - 무거운 OCR 작업은 Celery로 백그라운드 처리
   - 사용자는 실시간으로 진행률 확인 가능

2. **메모리 관리**
   - 대용량 PDF 처리 시 스트리밍 방식 사용
   - 이미지 처리 후 메모리 즉시 해제

3. **캐싱 전략**
   - Redis를 통한 처리 상태 캐싱
   - 정적 파일 CDN 배포

### 오류 처리
1. **견고한 에러 핸들링**
   - 각 처리 단계별 예외 처리
   - 사용자 친화적 오류 메시지
   - 로그를 통한 디버깅 정보 수집

2. **복구 메커니즘**
   - 실패한 작업 재시도 로직
   - 부분 처리 결과 보존

### 모니터링
1. **로깅**
   - 구조화된 로깅 (JSON 형태)
   - 처리 시간 및 성능 메트릭 수집
   - 오류 추적 및 알림

2. **헬스 체크**
   - API 엔드포인트 상태 확인
   - 의존 서비스 (Redis, Celery) 상태 확인

## 7. 일반적인 작업

### 새로운 OCR 엔진 추가
1. `core/ocr_engine.py`에서 새 엔진 클래스 구현
2. OCREngineManager에 엔진 등록
3. 설정 파일에 엔진 옵션 추가
4. 테스트 케이스 작성

### 새로운 전처리 옵션 추가
1. `core/image_processor.py`에 새 메서드 구현
2. `ProcessingOptions` 모델에 옵션 추가
3. 프론트엔드 설정 UI 업데이트
4. 테스트 케이스 작성

### API 엔드포인트 추가
1. 적절한 라우터 파일에 엔드포인트 추가
2. Pydantic 모델 정의
3. 비즈니스 로직 구현
4. API 테스트 작성
5. OpenAPI 문서 자동 생성 확인

### 프론트엔드 기능 추가
1. HTML 템플릿 수정
2. CSS 스타일링 추가
3. JavaScript 로직 구현
4. 반응형 디자인 확인
5. 브라우저 호환성 테스트

### 배포 환경 설정
1. 환경별 설정 파일 작성
2. Docker 이미지 빌드 및 테스트
3. 클라우드 리소스 프로비저닝
4. 모니터링 및 로깅 설정
5. CI/CD 파이프라인 구성

### 개발 워크플로우
1. **기능 개발**
   ```bash
   # 기능 브랜치 생성
   git checkout -b feature/new-feature
   
   # TDD 방식으로 개발
   # 1. 테스트 작성
   # 2. 최소 구현
   # 3. 리팩토링
   
   # 코드 품질 검사
   black . && flake8 . && mypy backend/
   
   # 테스트 실행
   pytest --cov=backend
   ```

2. **Pull Request**
   - 코드 리뷰 필수
   - CI 체크 통과 확인
   - 문서 업데이트

3. **배포**
   ```bash
   # 스테이징 배포
   docker-compose -f docker-compose.staging.yml up -d
   
   # 프로덕션 배포
   docker-compose -f docker-compose.prod.yml up -d
   ```

이 가이드를 통해 개발자는 프로젝트의 전체 구조를 이해하고, 효율적으로 개발 작업을 수행할 수 있습니다.