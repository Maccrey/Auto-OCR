# K-OCR Web Corrector - API 문서

## 📖 개요

K-OCR Web Corrector는 FastAPI 기반의 RESTful API를 제공합니다. 자동 생성된 OpenAPI 문서와 함께 상세한 사용법을 제공합니다.

## 🌐 API 문서 접근

### 자동 생성 문서
서비스 실행 후 다음 URL에서 대화형 API 문서에 접근할 수 있습니다:

- **Swagger UI**: `http://localhost:8000/api/docs`
  - 대화형 인터페이스
  - API 테스트 기능 제공
  - 요청/응답 예시 포함

- **ReDoc**: `http://localhost:8000/api/redoc`
  - 읽기 전용 문서
  - 더 상세한 설명 포함
  - 인쇄 친화적 형식

### OpenAPI 스키마
- **JSON 스키마**: `http://localhost:8000/openapi.json`
- 타사 도구와의 연동 가능
- 클라이언트 SDK 자동 생성 가능

## 🚀 API 엔드포인트 개요

### 1. 파일 업로드 API (`/api/upload`)

#### POST /api/upload
PDF 파일을 서버에 업로드합니다.

**요청:**
```http
POST /api/upload
Content-Type: multipart/form-data

파라미터:
- file: PDF 파일 (최대 50MB)
```

**응답:**
```json
{
  "upload_id": "uuid-string",
  "filename": "document.pdf",
  "file_size": 1024000,
  "upload_time": "2024-01-15T10:30:00",
  "status": "uploaded"
}
```

#### GET /api/upload/{upload_id}/status
업로드 상태를 확인합니다.

**요청:**
```http
GET /api/upload/abc123/status
```

**응답:**
```json
{
  "upload_id": "abc123",
  "status": "uploaded",
  "filename": "document.pdf",
  "upload_time": "2024-01-15T10:30:00"
}
```

### 2. 처리 API (`/api/process`)

#### POST /api/process/{upload_id}
업로드된 파일의 OCR 처리를 시작합니다.

**요청:**
```http
POST /api/process/abc123
Content-Type: application/json

{
  "ocr_engine": "paddleocr",
  "preprocessing": {
    "apply_clahe": true,
    "deskew_enabled": true,
    "noise_removal": true,
    "adaptive_threshold": true
  },
  "text_correction": {
    "spelling_correction": true,
    "spacing_correction": true
  },
  "dpi": 300,
  "confidence_threshold": 0.7
}
```

**응답:**
```json
{
  "process_id": "def456",
  "upload_id": "abc123",
  "status": "processing",
  "current_step": "pdf_conversion",
  "progress": 10,
  "estimated_time": 120
}
```

#### GET /api/process/{process_id}/status
처리 상태를 확인합니다.

**요청:**
```http
GET /api/process/def456/status
```

**응답:**
```json
{
  "process_id": "def456",
  "status": "processing",
  "current_step": "ocr_recognition",
  "progress": 75,
  "estimated_time": 30,
  "results": null
}
```

### 3. 다운로드 API (`/api/download`)

#### GET /api/download/{process_id}
처리 완료된 텍스트 파일을 다운로드합니다.

**요청:**
```http
GET /api/download/def456
Accept: text/plain
```

**응답:**
```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename="document.txt"

인식된 텍스트 내용...
```

## 🔧 FastAPI 문서 설정 개선

### main.py 설정 최적화

현재 설정:
```python
app = FastAPI(
    title="K-OCR Web Corrector",
    description="한국어 문서 OCR 및 교정 웹 서비스",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)
```

#### 권장 개선사항:

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="K-OCR Web Corrector API",
        version="1.0.0",
        description="""
        ## K-OCR Web Corrector

        한국어 문서 OCR 및 텍스트 교정을 위한 웹 API입니다.

        ### 주요 기능
        - PDF 파일 업로드 및 검증
        - 이미지 전처리 (대비 향상, 노이즈 제거 등)
        - 한국어 OCR 처리 (PaddleOCR, Tesseract)
        - 텍스트 자동 교정 (띄어쓰기, 맞춤법)
        - 실시간 처리 상태 추적

        ### 처리 워크플로우
        1. **업로드**: PDF 파일을 서버에 업로드
        2. **처리 시작**: OCR 설정을 지정하여 처리 시작
        3. **상태 확인**: 실시간으로 처리 진행률 확인
        4. **결과 다운로드**: 완료된 텍스트 파일 다운로드

        ### 지원 형식
        - **입력**: PDF 파일 (최대 50MB)
        - **출력**: UTF-8 텍스트 파일

        ### 제한사항
        - 동시 처리: 사용자당 1개 파일
        - 보관 기간: 24시간 후 자동 삭제
        - 파일 크기: 최대 50MB
        """,
        routes=app.routes,
        tags=[
            {
                "name": "upload",
                "description": "파일 업로드 관련 API"
            },
            {
                "name": "processing",
                "description": "OCR 처리 관련 API"
            },
            {
                "name": "download",
                "description": "결과 다운로드 관련 API"
            },
            {
                "name": "health",
                "description": "시스템 상태 확인 API"
            }
        ]
    )

    # API 정보 추가
    openapi_schema["info"]["contact"] = {
        "name": "K-OCR Support",
        "url": "https://github.com/your-repo/issues"
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }

    # 서버 정보 추가
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "개발 서버"
        },
        {
            "url": "https://your-domain.com",
            "description": "프로덕션 서버"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### API 모델 문서화 개선

#### 응답 모델 예시:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ProcessingStatus(str, Enum):
    """처리 상태 열거형"""
    PENDING = "pending"
    UPLOADING = "uploading"
    CONVERTING = "converting"
    PREPROCESSING = "preprocessing"
    OCR_PROCESSING = "ocr_processing"
    TEXT_CORRECTION = "text_correction"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadResponse(BaseModel):
    """파일 업로드 응답"""
    upload_id: str = Field(..., description="업로드 고유 ID", example="abc123")
    filename: str = Field(..., description="원본 파일명", example="document.pdf")
    file_size: int = Field(..., description="파일 크기 (바이트)", example=1024000)
    upload_time: str = Field(..., description="업로드 시간", example="2024-01-15T10:30:00")
    status: str = Field(default="uploaded", description="업로드 상태")

class ProcessingOptions(BaseModel):
    """OCR 처리 옵션"""
    ocr_engine: str = Field(
        default="paddleocr",
        description="OCR 엔진 (paddleocr, tesseract, ensemble)",
        example="paddleocr"
    )
    dpi: int = Field(
        default=300,
        ge=150,
        le=600,
        description="이미지 해상도 DPI",
        example=300
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.1,
        le=0.9,
        description="신뢰도 임계값",
        example=0.7
    )

class ProcessingResponse(BaseModel):
    """처리 응답"""
    process_id: str = Field(..., description="처리 고유 ID")
    upload_id: str = Field(..., description="업로드 ID")
    status: ProcessingStatus = Field(..., description="처리 상태")
    current_step: str = Field(..., description="현재 처리 단계")
    progress: int = Field(..., ge=0, le=100, description="진행률 (0-100)")
    estimated_time: Optional[int] = Field(None, description="예상 완료 시간 (초)")
    error_message: Optional[str] = Field(None, description="오류 메시지")

    class Config:
        schema_extra = {
            "example": {
                "process_id": "def456",
                "upload_id": "abc123",
                "status": "processing",
                "current_step": "ocr_recognition",
                "progress": 75,
                "estimated_time": 30,
                "error_message": None
            }
        }
```

### 엔드포인트 문서화 개선

#### 상세한 문서화 예시:

```python
@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(
        ...,
        description="업로드할 PDF 파일",
        media_type="application/pdf"
    )
):
    """
    PDF 파일 업로드

    PDF 파일을 서버에 업로드하고 고유 ID를 반환합니다.

    ## 요구사항
    - 파일 형식: PDF (.pdf)
    - 최대 크기: 50MB
    - 한 번에 하나의 파일만 업로드 가능

    ## 응답
    - 성공 시: 업로드 ID와 파일 정보 반환
    - 실패 시: HTTP 400/413 오류 반환

    ## 예시
    ```bash
    curl -X POST "http://localhost:8000/api/upload" \
         -H "Content-Type: multipart/form-data" \
         -F "file=@document.pdf"
    ```
    """
    # 구현 내용...
```

## 📋 API 사용 가이드

### 1. 기본 워크플로우

```python
import requests
import time

# 1. 파일 업로드
files = {'file': open('document.pdf', 'rb')}
response = requests.post('http://localhost:8000/api/upload', files=files)
upload_data = response.json()
upload_id = upload_data['upload_id']

# 2. 처리 시작
processing_options = {
    "ocr_engine": "paddleocr",
    "preprocessing": {
        "apply_clahe": True,
        "deskew_enabled": True,
        "noise_removal": True
    },
    "text_correction": {
        "spelling_correction": True,
        "spacing_correction": True
    }
}

response = requests.post(
    f'http://localhost:8000/api/process/{upload_id}',
    json=processing_options
)
process_data = response.json()
process_id = process_data['process_id']

# 3. 상태 확인 (폴링)
while True:
    response = requests.get(f'http://localhost:8000/api/process/{process_id}/status')
    status_data = response.json()

    if status_data['status'] == 'completed':
        print("처리 완료!")
        break
    elif status_data['status'] == 'failed':
        print(f"처리 실패: {status_data.get('error_message')}")
        break
    else:
        print(f"진행률: {status_data['progress']}%")
        time.sleep(2)

# 4. 결과 다운로드
response = requests.get(f'http://localhost:8000/api/download/{process_id}')
with open('result.txt', 'w', encoding='utf-8') as f:
    f.write(response.text)
```

### 2. JavaScript/브라우저에서 사용

```javascript
class KOCRClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('업로드 실패');
        }

        return await response.json();
    }

    async startProcessing(uploadId, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/process/${uploadId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(options)
        });

        return await response.json();
    }

    async getStatus(processId) {
        const response = await fetch(`${this.baseUrl}/api/process/${processId}/status`);
        return await response.json();
    }

    async downloadResult(processId) {
        const response = await fetch(`${this.baseUrl}/api/download/${processId}`);
        return await response.text();
    }

    async processFile(file, options = {}, onProgress = null) {
        // 1. 업로드
        const uploadData = await this.uploadFile(file);

        // 2. 처리 시작
        const processData = await this.startProcessing(uploadData.upload_id, options);

        // 3. 상태 모니터링
        return new Promise((resolve, reject) => {
            const checkStatus = async () => {
                try {
                    const status = await this.getStatus(processData.process_id);

                    if (onProgress) {
                        onProgress(status);
                    }

                    if (status.status === 'completed') {
                        const result = await this.downloadResult(processData.process_id);
                        resolve(result);
                    } else if (status.status === 'failed') {
                        reject(new Error(status.error_message));
                    } else {
                        setTimeout(checkStatus, 2000);
                    }
                } catch (error) {
                    reject(error);
                }
            };

            checkStatus();
        });
    }
}

// 사용 예시
const client = new KOCRClient();
const fileInput = document.getElementById('file-input');

fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
            const result = await client.processFile(
                file,
                {
                    ocr_engine: 'paddleocr',
                    preprocessing: { apply_clahe: true }
                },
                (status) => {
                    console.log(`진행률: ${status.progress}%`);
                }
            );
            console.log('처리 결과:', result);
        } catch (error) {
            console.error('처리 실패:', error);
        }
    }
});
```

## 🔒 인증 및 보안

### 현재 상태
- 인증 없이 공개 API로 제공
- CORS 모든 오리진 허용 (개발 환경)

### 프로덕션 권장 설정
```python
# 프로덕션용 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Rate Limiting 추가 (slowapi 사용)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 제한 적용
@router.post("/upload")
@limiter.limit("5/minute")
async def upload_file(request: Request, file: UploadFile):
    # 구현...
```

## 📊 모니터링 및 로깅

### 로그 설정
```python
import logging
import structlog

# 구조화된 로깅 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

@router.post("/upload")
async def upload_file(file: UploadFile):
    logger.info(
        "파일 업로드 시작",
        filename=file.filename,
        file_size=file.size,
        content_type=file.content_type
    )
    # 구현...
```

### 메트릭 수집
```python
from prometheus_client import Counter, Histogram, generate_latest
import time

# 메트릭 정의
upload_counter = Counter('uploads_total', '총 업로드 수')
processing_duration = Histogram('processing_duration_seconds', '처리 시간')

@router.post("/upload")
async def upload_file(file: UploadFile):
    upload_counter.inc()
    start_time = time.time()

    try:
        # 처리 로직
        result = await process_file(file)
        return result
    finally:
        processing_duration.observe(time.time() - start_time)

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## 🧪 API 테스트

### pytest를 이용한 API 테스트
```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_upload_valid_pdf():
    """유효한 PDF 업로드 테스트"""
    with open("test_files/sample.pdf", "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "upload_id" in data
    assert data["filename"] == "sample.pdf"

def test_upload_invalid_file():
    """잘못된 파일 형식 테스트"""
    with open("test_files/sample.txt", "rb") as f:
        response = client.post(
            "/api/upload",
            files={"file": ("sample.txt", f, "text/plain")}
        )

    assert response.status_code == 400

@pytest.mark.asyncio
async def test_processing_workflow():
    """전체 처리 워크플로우 테스트"""
    # 1. 파일 업로드
    with open("test_files/sample.pdf", "rb") as f:
        upload_response = client.post(
            "/api/upload",
            files={"file": ("sample.pdf", f, "application/pdf")}
        )

    upload_id = upload_response.json()["upload_id"]

    # 2. 처리 시작
    process_response = client.post(
        f"/api/process/{upload_id}",
        json={"ocr_engine": "paddleocr"}
    )

    assert process_response.status_code == 200
    process_id = process_response.json()["process_id"]

    # 3. 상태 확인
    status_response = client.get(f"/api/process/{process_id}/status")
    assert status_response.status_code == 200
```

## 📚 추가 리소스

### OpenAPI 스키마 내보내기
```bash
# OpenAPI JSON 스키마 다운로드
curl http://localhost:8000/openapi.json > api-schema.json

# 클라이언트 SDK 생성 (openapi-generator 사용)
openapi-generator generate -i api-schema.json -g python -o ./python-client
openapi-generator generate -i api-schema.json -g javascript -o ./js-client
```

### Postman 컬렉션
OpenAPI 스키마를 Postman으로 가져와서 API 테스트 컬렉션을 생성할 수 있습니다.

---

**마지막 업데이트**: 2024년 1월
**API 버전**: v1.0.0