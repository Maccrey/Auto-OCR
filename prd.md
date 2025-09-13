# K-OCR Corrector - 상세 제품 요구사항 문서 (PRD)

## AI 개발 최적화 버전

### 1. 제품 개요

**제품명**: K-OCR Corrector (한국어 문서 OCR & 교정 도구)

**목표**: PDF/이미지 문서를 정확한 한국어 텍스트로 변환하는 GUI 애플리케이션

**핵심 가치**:

- **정확성**: 최적화된 전처리와 교정으로 OCR 인식률 극대화
- **사용자 친화성**: 직관적인 GUI 환경
- **투명성**: 상세한 교정 리포트 제공

### 2. 아키텍처 설계

#### 2.1 전체 아키텍처

```
GUI Layer (PySide6)
├── Main Window
├── Settings Panel
├── Preview Panel
└── Report Panel

Business Logic Layer
├── Document Processor
├── OCR Engine Manager
├── Text Corrector
└── Report Generator

Data Layer
├── File Handler
├── Configuration Manager
└── Result Storage
```

#### 2.2 모듈 구조

```
k_ocr_corrector/
├── gui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── settings_panel.py
│   ├── preview_panel.py
│   └── report_panel.py
├── core/
│   ├── __init__.py
│   ├── document_processor.py
│   ├── ocr_engine.py
│   ├── text_corrector.py
│   └── report_generator.py
├── utils/
│   ├── __init__.py
│   ├── file_handler.py
│   ├── config_manager.py
│   └── image_processor.py
├── tests/
│   ├── __init__.py
│   ├── test_document_processor.py
│   ├── test_ocr_engine.py
│   ├── test_text_corrector.py
│   └── test_gui/
└── resources/
    ├── test_documents/
    └── config/
```

### 3. 상세 기능 요구사항

#### 3.1 Core Module 요구사항

##### 3.1.1 DocumentProcessor 클래스

**목적**: PDF/이미지 파일 처리 및 전처리 담당

**주요 메서드**:

```python
class DocumentProcessor:
    def load_file(self, file_path: str) -> bool
    def convert_pdf_to_images(self) -> List[Image]
    def preprocess_image(self, image: Image, options: PreprocessOptions) -> Image
    def get_preprocessing_preview(self, image: Image) -> Dict[str, Image]
```

**전처리 옵션**:

- 흑백 변환 + CLAHE 대비 보정
- Deskew (기울기 보정)
- 노이즈 제거 + 테두리 제거
- Adaptive Threshold 이진화
- 텍스트 슈퍼해상도 (선택사항)

##### 3.1.2 OCREngine 클래스

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

##### 3.1.3 TextCorrector 클래스

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

##### 3.1.4 ReportGenerator 클래스

**목적**: 교정 리포트 생성 및 통계 계산

**주요 메서드**:

```python
class ReportGenerator:
    def calculate_cer_wer(self, original: str, corrected: str) -> Tuple[float, float]
    def generate_diff_report(self, original: str, corrected: str) -> DiffReport
    def export_results(self, format: str, output_path: str) -> bool
```

#### 3.2 GUI Module 요구사항

##### 3.2.1 MainWindow 클래스

**기능**:

- 파일 드래그 앤 드롭 지원
- 메뉴바 및 툴바 제공
- 하위 패널들의 컨테이너 역할
- 진행 상태바 및 로그 표시

##### 3.2.2 SettingsPanel 클래스

**기능**:

- 전처리 옵션 설정 UI
- OCR 엔진 선택 UI
- 교정 옵션 설정 UI
- 설정 저장/불러오기

##### 3.2.3 PreviewPanel 클래스

**기능**:

- 탭 기반 미리보기 (원본/전처리/OCR/교정/diff)
- 이미지 확대/축소 기능
- 텍스트 편집 기능

##### 3.2.4 ReportPanel 클래스

**기능**:

- CER/WER 통계 표시
- 변경사항 하이라이트
- 내보내기 옵션

### 4. 데이터 모델

#### 4.1 핵심 데이터 클래스

```python
@dataclass
class PreprocessOptions:
    apply_clahe: bool = True
    deskew_enabled: bool = True
    noise_removal: bool = True
    adaptive_threshold: bool = True
    super_resolution: bool = False

@dataclass
class OCRResult:
    text: str
    confidence: float
    line_boxes: List[BoundingBox]
    engine_used: str

@dataclass
class CorrectionResult:
    original_text: str
    corrected_text: str
    corrections: List[CorrectionItem]
    cer_score: float
    wer_score: float

@dataclass
class DiffItem:
    line_number: int
    original: str
    corrected: str
    change_type: str  # 'insert', 'delete', 'replace'
```

### 5. 기술 스택 및 의존성

#### 5.1 필수 라이브러리

```
# GUI
PySide6>=6.5.0

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

# 리포트 생성
python-docx>=0.8.11
reportlab>=4.0.0
jinja2>=3.1.0

# 유틸리티
pydantic>=2.0.0
pyyaml>=6.0
```

#### 5.2 개발 도구

```
# 테스트
pytest>=7.4.0
pytest-qt>=4.2.0
pytest-cov>=4.1.0

# 코드 품질
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0

# 패키징
PyInstaller>=5.13.0
```

### 6. 품질 요구사항

#### 6.1 성능 요구사항

- **처리 속도**: 300dpi 기준 1페이지 ≤ 5초 (GPU 환경)
- **메모리 사용량**: 최대 2GB (500페이지 문서 기준)
- **OCR 정확도**: 교정 후 CER < 3%

#### 6.2 사용성 요구사항

- **학습 시간**: 비전문 사용자 5분 내 숙달
- **오류 허용**: 잘못된 입력에 대한 명확한 오류 메시지
- **접근성**: 키보드 단축키 및 스크린 리더 지원

#### 6.3 호환성 요구사항

- **OS**: Windows 10+, macOS 11+, Ubuntu 20.04+
- **Python**: 3.9+
- **파일 형식**: PDF, PNG, JPG, TIFF

### 7. 테스트 전략

#### 7.1 단위 테스트 범위

- 각 클래스의 모든 public 메서드
- 에러 케이스 및 경계값 테스트
- 코드 커버리지 > 85%

#### 7.2 통합 테스트 범위

- OCR 파이프라인 전체 플로우
- GUI 컴포넌트 간 상호작용
- 파일 I/O 및 설정 관리

#### 7.3 E2E 테스트 범위

- 실제 문서 처리 시나리오
- 다양한 문서 품질에 대한 테스트
- 사용자 워크플로우 테스트

### 8. 배포 전략

#### 8.1 패키징

- PyInstaller를 사용한 standalone 실행파일
- 플랫폼별 인스톨러 제공
- 필요한 모델 파일 포함

#### 8.2 버전 관리

- Semantic Versioning 적용
- 자동 업데이트 확인 기능
- 설정 마이그레이션 지원

### 9. 확장성 고려사항

#### 9.1 플러그인 아키텍처

- OCR 엔진 플러그인 인터페이스
- 교정 규칙 플러그인 인터페이스
- 내보내기 포맷 플러그인 인터페이스

#### 9.2 클라우드 확장

- API 서버 모드 지원 준비
- 배치 처리 기능
- 사용자 계정 및 프로젝트 관리

### 10. 보안 고려사항

#### 10.1 데이터 보안

- 로컬 처리 우선 (개인정보 보호)
- 임시 파일 자동 삭제
- 클라우드 API 키 암호화 저장

#### 10.2 입력 검증

- 파일 형식 및 크기 검증
- 악성 파일 검사
- 메모리 사용량 제한
