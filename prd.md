# K-OCR Web Corrector - 상세 제품 요구사항 문서 (PRD)
## AI 개발 최적화 웹 버전

### 1. 제품 개요

**제품명**: K-OCR Web Corrector (한국어 문서 OCR & 교정 웹 서비스)

**목표**: PDF 문서를 업로드하여 PNG로 변환 후 전처리 및 OCR을 통해 정확한 한국어 텍스트 파일로 다운로드할 수 있는 웹 애플리케이션

**핵심 가치**:
- **정확성**: 최적화된 전처리와 교정으로 OCR 인식률 극대화
- **사용자 친화성**: 직관적인 웹 인터페이스
- **편의성**: 브라우저만으로 접근 가능한 웹 서비스
- **효율성**: PDF 업로드 → PNG 변환 → 전처리 → OCR → 텍스트 다운로드의 간소화된 워크플로우

### 2. 아키텍처 설계

#### 2.1 전체 아키텍처
```
Frontend Layer (HTML/CSS/JavaScript)
├── File Upload Interface
├── Progress Display
├── Settings Panel (간소화)
└── Download Interface

Backend API Layer (FastAPI)
├── File Upload Endpoint
├── Processing Status Endpoint
├── Settings Configuration Endpoint
└── Result Download Endpoint

Business Logic Layer
├── PDF Converter (PDF → PNG)
├── Image Preprocessor
├── OCR Engine Manager
├── Text Corrector
└── File Generator

Data Layer
├── Temporary File Storage
├── Configuration Manager
└── Result Cache
```

#### 2.2 모듈 구조
```
k_ocr_web_corrector/
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/
│       ├── index.html
│       ├── upload.html
│       └── result.html
├── backend/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── processing.py
│   │   └── download.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pdf_converter.py
│   │   ├── image_processor.py
│   │   ├── ocr_engine.py
│   │   ├── text_corrector.py
│   │   └── file_generator.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_handler.py
│   │   ├── config_manager.py
│   │   └── temp_storage.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── test_api/
│   ├── test_core/
│   └── test_utils/
├── temp_storage/
├── config/
└── requirements.txt
```

### 3. 상세 기능 요구사항

#### 3.1 Core Module 요구사항

##### 3.1.1 PDFConverter 클래스
**목적**: 업로드된 PDF 파일을 PNG 이미지로 변환

**주요 메서드**:
```python
class PDFConverter:
    def convert_pdf_to_png(self, pdf_path: str, output_dir: str) -> List[str]
    def validate_pdf(self, pdf_path: str) -> bool
    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]
    def estimate_processing_time(self, pdf_path: str) -> int
```

##### 3.1.2 ImageProcessor 클래스
**목적**: PNG 이미지 전처리 및 품질 향상

**주요 메서드**:
```python
class ImageProcessor:
    def preprocess_image(self, image_path: str, options: PreprocessOptions) -> str
    def apply_clahe(self, image_path: str) -> str
    def deskew_image(self, image_path: str) -> str
    def remove_noise(self, image_path: str) -> str
    def adaptive_threshold(self, image_path: str) -> str
```

**전처리 옵션**:
- 흑백 변환 + CLAHE 대비 보정
- Deskew (기울기 보정)
- 노이즈 제거 + 테두리 제거
- Adaptive Threshold 이진화
- 텍스트 슈퍼해상도 (선택사항)

##### 3.1.3 OCREngine 클래스
**목적**: 다중 OCR 엔진 관리 및 실행

**주요 메서드**:
```python
class OCREngine:
    def set_engine(self, engine_type: str) -> None
    def recognize_text(self, image: Image) -> OCRResult
    def ensemble_recognition(self, image: Image, engines: List[str]) -> OCRResult
    def get_confidence_scores(self) -> Dict[str, float]
```

**지원 엔진**:
- PaddleOCR (korean) - 기본 엔진
- Tesseract (kor) - 보조 엔진
- 클라우드 API (Google, Naver, MS) - 선택사항

##### 3.1.4 TextCorrector 클래스
**목적**: 한국어 텍스트 교정 및 후처리

**주요 메서드**:
```python
class TextCorrector:
    def correct_spacing(self, text: str) -> str
    def correct_spelling(self, text: str) -> str
    def apply_custom_rules(self, text: str) -> str
    def get_correction_diff(self, original: str, corrected: str) -> List[DiffItem]
```

**교정 기능**:
- KoSpacing을 이용한 띄어쓰기 교정
- Hanspell을 이용한 맞춤법 교정
- 사용자 정의 사전 적용
- OCR 오류 패턴 규칙 기반 교정

##### 3.1.5 FileGenerator 클래스
**목적**: 최종 텍스트 파일 생성 및 다운로드 준비

**주요 메서드**:
```python
class FileGenerator:
    def generate_text_file(self, corrected_text: str, output_path: str) -> str
    def create_download_response(self, file_path: str) -> Response
    def cleanup_temp_files(self, file_paths: List[str]) -> None
    def get_file_download_url(self, file_id: str) -> str
```

#### 3.2 Web API Module 요구사항

##### 3.2.1 Upload API (api/upload.py)
**기능**:
- PDF 파일 업로드 처리
- 파일 검증 및 임시 저장
- 업로드 진행률 추적
- 업로드 완료 후 처리 작업 ID 반환

**엔드포인트**:
```python
POST /api/upload - PDF 파일 업로드
GET /api/upload/{upload_id}/status - 업로드 상태 확인
```

##### 3.2.2 Processing API (api/processing.py)
**기능**:
- PDF → PNG 변환 진행률 추적
- 전처리 및 OCR 처리 상태 관리
- 텍스트 교정 진행률 추적
- 실시간 상태 업데이트

**엔드포인트**:
```python
POST /api/process/{upload_id} - 처리 시작
GET /api/process/{process_id}/status - 처리 상태 확인
POST /api/process/{process_id}/settings - 처리 옵션 설정
```

##### 3.2.3 Download API (api/download.py)
**기능**:
- 완료된 텍스트 파일 다운로드
- 임시 파일 정리
- 다운로드 링크 만료 관리

**엔드포인트**:
```python
GET /api/download/{process_id} - 결과 파일 다운로드
DELETE /api/download/{process_id} - 임시 파일 삭제
```

##### 3.2.4 Frontend Templates
**기능**:
- 파일 업로드 인터페이스 (drag & drop)
- 실시간 진행률 표시
- 간단한 설정 옵션
- 결과 다운로드 페이지

### 4. 데이터 모델

#### 4.1 핵심 데이터 클래스
```python
@dataclass
class UploadRequest:
    file_id: str
    filename: str
    file_size: int
    upload_time: datetime

@dataclass
class ProcessingOptions:
    apply_clahe: bool = True
    deskew_enabled: bool = True
    noise_removal: bool = True
    adaptive_threshold: bool = True
    super_resolution: bool = False
    ocr_engine: str = "paddleocr"

@dataclass
class ProcessingStatus:
    process_id: str
    status: str  # 'pending', 'converting', 'preprocessing', 'ocr', 'correcting', 'completed', 'failed'
    progress: int  # 0-100
    current_step: str
    estimated_time_remaining: int
    error_message: Optional[str] = None

@dataclass
class ProcessingResult:
    process_id: str
    original_filename: str
    total_pages: int
    processing_time: float
    final_text: str
    download_url: str
    expires_at: datetime

@dataclass
class OCRResult:
    text: str
    confidence: float
    engine_used: str
    processing_time: float
```

### 5. 기술 스택 및 의존성

#### 5.1 필수 라이브러리
```
# Web Framework
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6

# Template Engine
jinja2>=3.1.0

# File Processing
pdf2image>=1.16.0
pypdf>=3.16.0

# OCR
paddleocr>=2.7.0
pytesseract>=0.3.10

# 이미지 처리
opencv-python>=4.8.0
Pillow>=10.0.0
scikit-image>=0.21.0

# 텍스트 교정
kospacing>=0.4.0
py-hanspell>=1.1.0

# 비동기 처리
celery>=5.3.0
redis>=5.0.0

# 유틸리티
pydantic>=2.0.0
python-dotenv>=1.0.0
aiofiles>=23.2.0
```

#### 5.2 개발 도구
```
# 테스트
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0  # FastAPI 테스트용

# 코드 품질
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0

# 배포
gunicorn>=21.2.0
docker>=6.1.0
```

### 6. 품질 요구사항

#### 6.1 성능 요구사항
- **처리 속도**: 300dpi 기준 1페이지 ≤ 10초 (웹 환경)
- **동시 처리**: 최대 10개 요청 동시 처리 가능
- **파일 크기 제한**: 최대 50MB PDF 파일
- **OCR 정확도**: 교정 후 CER < 3%
- **응답 시간**: API 응답 시간 < 2초

#### 6.2 사용성 요구사항
- **직관성**: 별도 설치 없이 브라우저에서 즉시 사용 가능
- **반응성**: 실시간 진행률 표시 및 상태 업데이트
- **오류 처리**: 명확한 오류 메시지 및 복구 가이드
- **접근성**: 모바일 브라우저 지원

#### 6.3 호환성 요구사항
- **브라우저**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Python**: 3.9+
- **파일 형식**: PDF (업로드), TXT (다운로드)
- **서버 환경**: Linux Ubuntu 20.04+, Docker 지원

### 7. 테스트 전략

#### 7.1 단위 테스트 범위
- 각 클래스의 모든 public 메서드
- 에러 케이스 및 경계값 테스트
- 코드 커버리지 > 85%

#### 7.2 통합 테스트 범위
- 전체 OCR 파이프라인 API 테스트
- 비동기 작업 처리 테스트
- 파일 업로드/다운로드 테스트
- 데이터베이스 연동 테스트

#### 7.3 E2E 테스트 범위
- 웹 브라우저 자동화 테스트 (Selenium)
- 실제 PDF 문서 업로드부터 텍스트 다운로드까지
- 다양한 브라우저 호환성 테스트
- 동시 사용자 부하 테스트

### 8. 배포 전략

#### 8.1 컨테이너화
- Docker를 이용한 애플리케이션 컨테이너화
- Docker Compose를 통한 멀티 컨테이너 구성 (웹서버, Redis, Celery worker)
- 필요한 OCR 모델 파일을 포함한 이미지 빌드

#### 8.2 클라우드 배포
- AWS/GCP/Azure 클라우드 플랫폼 지원
- 로드 밸런서 및 오토 스케일링 설정
- CDN을 통한 정적 파일 배포

### 9. 확장성 고려사항

#### 9.1 마이크로서비스 아키텍처
- OCR 엔진별 독립 서비스
- 파일 처리 전용 서비스
- 텍스트 교정 전용 서비스

#### 9.2 확장 기능
- 사용자 인증 및 세션 관리
- 처리 이력 및 통계 대시보드
- 배치 처리 API (다중 파일 처리)

### 10. 보안 고려사항

#### 10.1 데이터 보안
- 업로드된 파일 임시 저장 및 자동 삭제 (TTL: 24시간)
- HTTPS 통신 강제
- 파일 접근 권한 제한 (업로더만 다운로드 가능)
- 민감 정보 로깅 방지

#### 10.2 입력 검증
- 파일 형식 검증 (PDF만 허용)
- 파일 크기 제한 (최대 50MB)
- 업로드 속도 제한 (Rate Limiting)
- CSRF 토큰 검증