# K-OCR Web Corrector - 시스템 아키텍처 문서

## 🏗️ 전체 시스템 아키텍처

### 개요
K-OCR Web Corrector는 마이크로서비스 아키텍처 원칙을 따르는 웹 기반 OCR 서비스입니다. FastAPI 기반 백엔드와 Vanilla JavaScript 프론트엔드로 구성되며, 비동기 작업 처리를 위해 Celery를 사용합니다.

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Web Browser (Chrome/Firefox/Safari/Edge)                         │
│  ├─── HTML5 (Semantic Markup)                                     │
│  ├─── CSS3 (Responsive Design + Dark Mode)                        │
│  └─── JavaScript (ES6+ / Vanilla JS)                              │
│       ├─── main.js (App Logic)                                    │
│       ├─── upload.js (File Upload)                                │
│       ├─── settings.js (Configuration)                            │
│       └─── progress.js (Real-time Updates)                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/HTTPS + WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                             │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Web Framework (Python 3.11)                             │
│  ├─── CORS Middleware                                             │
│  ├─── Rate Limiting                                               │
│  ├─── Request Validation (Pydantic)                               │
│  ├─── OpenAPI Documentation                                       │
│  └─── Static File Serving                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Internal API Calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Business Logic Layer                           │
├─────────────────────────────────────────────────────────────────────┤
│  API Routers                     │  Core Processing Modules        │
│  ├─── upload.py                  │  ├─── pdf_converter.py          │
│  ├─── processing.py              │  ├─── image_processor.py        │
│  ├─── download.py                │  ├─── ocr_engine.py             │
│  └─── frontend.py                │  ├─── text_corrector.py         │
│                                  │  └─── file_generator.py         │
│                                  │                                 │
│  Background Tasks (Celery)       │  Utility Modules                │
│  └─── tasks.py                   │  ├─── temp_storage.py           │
│                                  │  ├─── config_manager.py         │
│                                  │  └─── file_handler.py           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Queue Management
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Message Broker Layer                            │
├─────────────────────────────────────────────────────────────────────┤
│  Redis (In-Memory Data Store)                                     │
│  ├─── Task Queue (Celery Broker)                                  │
│  ├─── Result Backend (Celery Results)                             │
│  ├─── Session Storage                                             │
│  ├─── Cache Management                                            │
│  └─── Real-time Data                                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Worker Process Management
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Processing Workers                               │
├─────────────────────────────────────────────────────────────────────┤
│  Celery Workers (Multi-Process)                                   │
│  ├─── PDF Processing Worker                                       │
│  ├─── OCR Processing Worker                                       │
│  ├─── Text Correction Worker                                      │
│  └─── File Generation Worker                                      │
│                                                                    │
│  External OCR Engines                                             │
│  ├─── PaddleOCR (Primary)                                         │
│  ├─── Tesseract (Secondary)                                       │
│  └─── Ensemble Mode (Combined)                                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ File System Operations
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Storage Layer                                 │
├─────────────────────────────────────────────────────────────────────┤
│  File System Storage                                              │
│  ├─── temp_storage/ (Temporary Files)                             │
│  │    ├─── uploads/ (Original PDFs)                               │
│  │    ├─── converted/ (PNG Images)                                │
│  │    ├─── processed/ (Processed Images)                          │
│  │    └─── results/ (Output Text Files)                           │
│  │                                                                │
│  └─── Static Assets                                               │
│       ├─── frontend/static/css/                                   │
│       ├─── frontend/static/js/                                    │
│       └─── frontend/static/images/                                │
└─────────────────────────────────────────────────────────────────────┘
```

## 🎯 핵심 설계 원칙

### 1. 관심사 분리 (Separation of Concerns)
- **프론트엔드**: 사용자 인터페이스와 상호작용만 담당
- **API 레이어**: HTTP 요청 처리 및 비즈니스 로직 호출
- **비즈니스 로직**: 실제 OCR 처리 및 데이터 변환
- **데이터 레이어**: 파일 저장 및 임시 데이터 관리

### 2. 비동기 처리 (Asynchronous Processing)
- 시간이 오래 걸리는 OCR 작업은 백그라운드에서 처리
- 사용자는 실시간으로 진행률 확인 가능
- 시스템 자원의 효율적 사용

### 3. 확장성 (Scalability)
- Celery Worker를 통한 수평 확장 가능
- Redis를 통한 상태 관리로 다중 인스턴스 지원
- Docker 컨테이너화로 클라우드 배포 용이

### 4. 신뢰성 (Reliability)
- 각 처리 단계별 오류 처리
- 파일 임시 저장을 통한 데이터 보호
- 자동 정리 메커니즘으로 디스크 공간 관리

## 📦 모듈별 상세 아키텍처

### Frontend Architecture (SPA - Single Page Application)

```
frontend/
├── templates/
│   └── index.html (Single HTML Template)
├── static/
│   ├── css/
│   │   ├── main.css (Global Styles)
│   │   ├── upload.css (Upload UI Styles)
│   │   └── progress.css (Progress UI Styles)
│   ├── js/
│   │   ├── main.js (App Controller)
│   │   ├── upload.js (Upload Manager)
│   │   ├── settings.js (Settings Manager)
│   │   └── progress.js (Progress Monitor)
│   └── images/
│       └── icons/ (UI Icons)

Data Flow:
User Input → Event Handler → API Call → DOM Update
```

#### 주요 설계 특징:
- **모듈러 설계**: 각 기능별로 독립적인 JavaScript 모듈
- **이벤트 기반**: 사용자 액션과 서버 응답에 따른 상태 변경
- **반응형 디자인**: CSS Grid/Flexbox를 활용한 모바일 대응
- **접근성 준수**: WCAG 2.1 가이드라인 준수

### Backend API Architecture (Layered Architecture)

```
backend/
├── api/ (Presentation Layer)
│   ├── upload.py (File Upload Endpoints)
│   ├── processing.py (OCR Processing Endpoints)
│   ├── download.py (File Download Endpoints)
│   └── frontend.py (Frontend Serving)
├── core/ (Business Logic Layer)
│   ├── pdf_converter.py (PDF → PNG Conversion)
│   ├── image_processor.py (Image Enhancement)
│   ├── ocr_engine.py (Text Recognition)
│   ├── text_corrector.py (Text Post-processing)
│   ├── file_generator.py (Result File Generation)
│   └── tasks.py (Celery Background Tasks)
├── utils/ (Infrastructure Layer)
│   ├── temp_storage.py (File Management)
│   ├── config_manager.py (Configuration)
│   └── file_handler.py (File Operations)
└── main.py (Application Entry Point)

Request Flow:
HTTP Request → FastAPI Router → Business Logic → Celery Task → Response
```

#### 주요 설계 패턴:
- **Repository Pattern**: 데이터 액세스 추상화
- **Factory Pattern**: OCR 엔진 생성 및 관리
- **Strategy Pattern**: 다양한 OCR 엔진 지원
- **Observer Pattern**: 처리 상태 실시간 업데이트

### Data Processing Pipeline

```
Input PDF File
       │
       ▼
┌─────────────────┐
│  File Upload    │ ← temp_storage.py
│  & Validation   │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  PDF → PNG      │ ← pdf_converter.py (PyMuPDF)
│  Conversion     │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  Image          │ ← image_processor.py (OpenCV)
│  Preprocessing  │   - CLAHE (대비 향상)
└─────────────────┘   - Deskew (기울기 보정)
       │               - Noise Removal (노이즈 제거)
       ▼               - Adaptive Threshold (이진화)
┌─────────────────┐
│  OCR Text       │ ← ocr_engine.py
│  Recognition    │   - PaddleOCR (Primary)
└─────────────────┘   - Tesseract (Secondary)
       │               - Ensemble Mode
       ▼
┌─────────────────┐
│  Text           │ ← text_corrector.py
│  Correction     │   - KoSpacing (띄어쓰기)
└─────────────────┘   - Hanspell (맞춤법)
       │               - Custom Rules
       ▼
┌─────────────────┐
│  File           │ ← file_generator.py
│  Generation     │   - UTF-8 Text File
└─────────────────┘   - Download Response
       │
       ▼
   Result File
```

### Asynchronous Task Architecture

```
FastAPI Process (Web Server)
       │
       │ Task Submission
       ▼
┌─────────────────────────────────────┐
│            Redis Queue              │
│                                     │
│ ┌─────────────┐ ┌─────────────────┐ │
│ │ Task Queue  │ │ Result Backend  │ │
│ │ (Pending)   │ │ (Completed)     │ │
│ └─────────────┘ └─────────────────┘ │
└─────────────────────────────────────┘
       │                     ▲
       │ Task Distribution   │ Result Storage
       ▼                     │
┌─────────────────────────────────────┐
│         Celery Workers              │
│                                     │
│ Worker 1    Worker 2    Worker 3    │
│ [PDF Conv]  [OCR Proc]  [Text Corr] │
│                                     │
│ Each worker processes tasks         │
│ independently and reports progress  │
└─────────────────────────────────────┘

Task Flow:
1. API receives request → Creates Celery task
2. Task queued in Redis → Worker picks up task
3. Worker processes → Updates progress in Redis
4. Task completes → Result stored in Redis
5. API polls results → Returns to client
```

## 🔧 기술 스택 세부사항

### Backend Technologies

#### Core Framework
```python
# FastAPI - Modern Python web framework
- Version: 0.104.0+
- Features: Automatic OpenAPI docs, Type hints, Async support
- Performance: ~25,000 requests/second (single instance)
```

#### Async Task Processing
```python
# Celery - Distributed task queue
- Broker: Redis
- Serializer: JSON
- Task routing: Round-robin
- Retry mechanism: Exponential backoff
```

#### OCR Engines
```python
# PaddleOCR - Deep learning OCR
- Models: Korean language pack
- Accuracy: ~95% on clean text
- GPU acceleration: Optional

# Tesseract - Traditional OCR
- Language: Korean (kor)
- Accuracy: ~90% on clean text
- CPU-based processing
```

#### Image Processing
```python
# OpenCV - Computer vision library
- CLAHE: Contrast Limited Adaptive Histogram Equalization
- Deskew: Hough transform for angle detection
- Denoising: Non-local means denoising
- Threshold: Adaptive Gaussian threshold
```

### Frontend Technologies

#### Modern Web Standards
```javascript
// ES6+ JavaScript features used:
- Async/Await for API calls
- Modules for code organization
- Arrow functions for cleaner syntax
- Destructuring for data extraction
- Template literals for string formatting
```

#### CSS Architecture
```css
/* BEM Methodology for CSS naming */
.block__element--modifier

/* CSS Custom Properties for theming */
:root {
  --primary-color: #007bff;
  --success-color: #28a745;
  --error-color: #dc3545;
}

/* CSS Grid for responsive layouts */
.container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
}
```

### Infrastructure Components

#### Message Broker (Redis)
```redis
# Configuration for production
maxmemory 2gb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60

# Data structures used:
- Strings: Task metadata
- Hashes: Processing status
- Lists: Task queues
- Sets: Active workers
```

#### File Storage Strategy
```
Temporary Storage Hierarchy:
temp_storage/
├── uploads/
│   └── {upload_id}/
│       └── original.pdf (24h TTL)
├── processing/
│   └── {process_id}/
│       ├── pages/ (PNG files)
│       ├── processed/ (Enhanced images)
│       └── ocr_results/ (Raw OCR output)
└── results/
    └── {process_id}/
        └── final.txt (24h TTL)

Cleanup Strategy:
- Automatic cleanup every hour
- Files older than 24 hours deleted
- Failed processing files cleaned immediately
```

## 📊 성능 특성 및 최적화

### Throughput Analysis
```
Single Instance Performance:
- File uploads: 100 concurrent users
- PDF conversion: 5-10 pages/second
- OCR processing: 2-5 pages/second (depends on complexity)
- Text generation: 50 files/second

Scalability Limits:
- Memory usage: ~2GB per OCR worker
- Disk I/O: ~100MB/s sustained
- Network I/O: ~1Gbps for file transfers
```

### Caching Strategy
```python
# Multi-level caching approach
L1 Cache: In-memory (Python dict) - Function results
L2 Cache: Redis - API responses and processed data
L3 Cache: File system - Converted images and OCR models

# Cache invalidation
- TTL-based expiration for temporary data
- Manual invalidation for configuration changes
- LRU eviction for memory management
```

### Database Design (Future PostgreSQL Integration)
```sql
-- Core tables for persistent storage
CREATE TABLE uploads (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    upload_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'uploaded'
);

CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY,
    upload_id UUID REFERENCES uploads(id),
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP NULL,
    error_message TEXT NULL
);

CREATE TABLE processing_results (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES processing_jobs(id),
    final_text TEXT NOT NULL,
    confidence_score FLOAT,
    processing_options JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_uploads_status ON uploads(status);
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_created ON processing_jobs(created_at);
```

## 🔒 보안 아키텍처

### Authentication & Authorization (Future)
```python
# JWT-based authentication design
class SecurityConfig:
    JWT_SECRET_KEY = "your-secret-key"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    # Rate limiting
    UPLOAD_RATE_LIMIT = "5/minute"
    API_RATE_LIMIT = "100/minute"

    # File validation
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {".pdf"}
    VIRUS_SCAN_ENABLED = True
```

### Data Protection
```python
# File security measures
class FileSecurityManager:
    @staticmethod
    def validate_file_type(file_content: bytes) -> bool:
        """Magic number validation for PDF files"""
        return file_content.startswith(b'%PDF-')

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove dangerous characters from filename"""
        return re.sub(r'[^\w\-_\.]', '_', filename)

    @staticmethod
    def generate_secure_id() -> str:
        """Generate cryptographically secure unique ID"""
        return secrets.token_urlsafe(32)
```

### Network Security
```nginx
# Nginx configuration for production
upstream fastapi {
    server web:8000;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # File upload limits
    client_max_body_size 50m;

    location / {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🚀 배포 아키텍처

### Containerized Deployment
```yaml
# Docker Compose Production Setup
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure

  worker:
    build: .
    command: celery -A backend.core.tasks worker
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    deploy:
      replicas: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    deploy:
      restart_policy:
        condition: on-failure

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - web

volumes:
  redis_data:
```

### Cloud Architecture (AWS/GCP/Azure)
```
Internet Gateway
       │
       ▼
┌─────────────────────────────────────┐
│          Load Balancer              │
│     (ALB/GLB/Azure Load Balancer)   │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│        Auto Scaling Group           │
│                                     │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │Web Srv 1│ │Web Srv 2│ │Web Srv 3│ │
│ └─────────┘ └─────────┘ └─────────┘ │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│         Worker Cluster              │
│                                     │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │Worker 1 │ │Worker 2 │ │Worker N │ │
│ └─────────┘ └─────────┘ └─────────┘ │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│       Managed Services              │
│                                     │
│ ┌─────────────┐ ┌─────────────────┐ │
│ │Redis Cluster│ │Object Storage   │ │
│ │(ElastiCache)│ │(S3/GCS/Blob)    │ │
│ └─────────────┘ └─────────────────┘ │
└─────────────────────────────────────┘
```

## 📈 모니터링 및 관측성

### Logging Architecture
```python
# Structured logging with correlation IDs
import structlog
import uuid

def setup_logging():
    structlog.configure(
        processors=[
            add_correlation_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.testing.LogCapture,
    )

def add_correlation_id(_, __, event_dict):
    event_dict["correlation_id"] = getattr(
        contextvars.correlation_id, None
    ) or str(uuid.uuid4())
    return event_dict
```

### Metrics Collection
```python
# Prometheus metrics integration
from prometheus_client import Counter, Histogram, Gauge

# Application metrics
UPLOADS_TOTAL = Counter('uploads_total', 'Total file uploads')
PROCESSING_TIME = Histogram('processing_duration_seconds', 'Processing time')
ACTIVE_JOBS = Gauge('active_jobs_count', 'Currently active processing jobs')
ERROR_RATE = Counter('errors_total', 'Total errors', ['error_type'])

# Business metrics
OCR_ACCURACY = Histogram('ocr_accuracy_score', 'OCR confidence scores')
FILE_SIZE_DIST = Histogram('file_size_bytes', 'Distribution of file sizes')
```

### Health Check Architecture
```python
# Multi-level health checks
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health/ready")
async def readiness_check():
    # Check external dependencies
    checks = {
        "redis": await check_redis_connection(),
        "disk_space": await check_disk_space(),
        "workers": await check_celery_workers()
    }

    all_healthy = all(checks.values())
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }

@app.get("/health/live")
async def liveness_check():
    # Minimal check for process health
    return {"status": "alive", "timestamp": datetime.utcnow()}
```

## 🔄 데이터 흐름 다이어그램

### Request-Response Flow
```
Client Side:                  Server Side:
┌─────────────┐              ┌─────────────────┐
│File Upload  │─────────────▶│FastAPI Endpoint │
└─────────────┘              └─────────────────┘
       │                              │
       │                              ▼
       │                     ┌─────────────────┐
       │                     │File Validation  │
       │                     └─────────────────┘
       │                              │
       │                              ▼
       │                     ┌─────────────────┐
       │                     │Celery Task      │◀────┐
       │                     │Creation         │     │
       │                     └─────────────────┘     │
       │                              │              │
       ▼                              ▼              │
┌─────────────┐              ┌─────────────────┐     │
│Progress UI  │◀─────────────│Task Status      │     │
│Updates      │              │Endpoint         │     │
└─────────────┘              └─────────────────┘     │
       │                              │              │
       │                              │         ┌────┴─────┐
       │                              │         │Background│
       │                              │         │Worker    │
       │                              │         └────┬─────┘
       │                              │              │
       ▼                              │              ▼
┌─────────────┐                       │     ┌─────────────────┐
│Download     │◀──────────────────────┴─────│Processing       │
│Result       │                             │Complete         │
└─────────────┘                             └─────────────────┘
```

## 🎛️ 구성 관리

### Environment Configuration
```python
# backend/config/settings.py
from pydantic import BaseSettings
from typing import List, Optional
from enum import Enum

class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class Settings(BaseSettings):
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    redis_url: str = "redis://localhost:6379/0"

    # File Storage
    temp_storage_path: str = "./temp_storage"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    file_retention_hours: int = 24

    # OCR Settings
    default_ocr_engine: str = "paddleocr"
    default_dpi: int = 300
    confidence_threshold: float = 0.7

    # Security
    secret_key: str
    cors_origins: List[str] = ["*"]

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_routes: dict = {
        'backend.core.tasks.process_document': {'queue': 'ocr_queue'}
    }

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

**마지막 업데이트**: 2024년 1월
**아키텍처 버전**: v1.0
**문서 작성자**: 개발팀