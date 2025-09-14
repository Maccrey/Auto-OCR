# K-OCR Web Corrector - 개발 환경 설정 가이드

## 🛠️ 개발 환경 개요

이 가이드는 K-OCR Web Corrector 프로젝트의 로컬 개발 환경을 설정하는 방법을 안내합니다.

## 📋 시스템 요구사항

### 필수 소프트웨어
- **Python 3.9+** (권장: Python 3.11)
- **Node.js 16+** (프론트엔드 도구용)
- **Redis** (메시지 브로커)
- **Git** (버전 관리)
- **Docker & Docker Compose** (선택사항, 권장)

### 권장 하드웨어
- **RAM**: 8GB 이상
- **저장공간**: 10GB 여유공간
- **CPU**: 4코어 이상 (OCR 처리 성능)

### 개발 도구 (권장)
- **IDE**: VSCode, PyCharm, 또는 선호하는 에디터
- **터미널**: Windows Terminal, iTerm2, 또는 기본 터미널
- **API 클라이언트**: Postman, Insomnia
- **데이터베이스 클라이언트**: Redis Insight

## 🚀 빠른 시작

### 1단계: 저장소 클론
```bash
git clone <repository-url>
cd AutoOCR
```

### 2단계: 가상환경 설정
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### 3단계: 의존성 설치
```bash
# Python 패키지 설치
pip install -r requirements.txt

# 개발용 의존성 설치
pip install -r requirements-dev.txt
```

### 4단계: 환경변수 설정
```bash
# 환경변수 파일 복사
cp .env.example .env

# .env 파일 편집 (선택사항)
# nano .env 또는 선호하는 에디터로 편집
```

### 5단계: Redis 서버 실행
```bash
# 로컬 Redis 설치 및 실행 (macOS)
brew install redis
brew services start redis

# 또는 Docker 사용
docker run -d --name redis -p 6379:6379 redis:latest
```

### 6단계: 개발 서버 실행
```bash
# FastAPI 서버 실행 (터미널 1)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Celery Worker 실행 (터미널 2)
celery -A backend.core.tasks worker --loglevel=info

# (선택사항) Flower 모니터링 (터미널 3)
celery -A backend.core.tasks flower
```

### 7단계: 서비스 접속 확인
- **웹 애플리케이션**: http://localhost:8000
- **API 문서**: http://localhost:8000/api/docs
- **Flower 모니터링**: http://localhost:5555 (실행한 경우)

## 🔧 상세 설정 가이드

### Python 환경 설정

#### 1. Python 버전 확인
```bash
python --version
# Python 3.9.0 이상이어야 함

# pyenv 사용하는 경우
pyenv install 3.11.0
pyenv global 3.11.0
```

#### 2. 가상환경 도구 선택
```bash
# 방법 1: venv (기본 권장)
python -m venv venv

# 방법 2: conda
conda create -n k-ocr python=3.11
conda activate k-ocr

# 방법 3: poetry
poetry install
poetry shell
```

#### 3. 의존성 관리
```bash
# 패키지 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 새 패키지 추가 후 requirements 업데이트
pip freeze > requirements.txt

# 개발용 패키지만 별도 관리
echo "pytest>=7.4.0" >> requirements-dev.txt
```

### 환경변수 설정

#### .env 파일 구성
```bash
# .env 파일 예시
# 환경 설정
ENVIRONMENT=development
DEBUG=true

# 서버 설정
HOST=0.0.0.0
PORT=8000

# Redis 설정
REDIS_URL=redis://localhost:6379/0

# Celery 설정
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 파일 저장 설정
TEMP_STORAGE_PATH=./temp_storage
MAX_FILE_SIZE=52428800  # 50MB
FILE_RETENTION_HOURS=24

# OCR 설정
DEFAULT_OCR_ENGINE=paddleocr
DEFAULT_DPI=300
DEFAULT_CONFIDENCE_THRESHOLD=0.7

# 보안 설정 (개발용)
SECRET_KEY=development-secret-key
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# 로깅 설정
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### 환경별 설정 파일
```bash
# 개발 환경
cp .env.example .env.development

# 테스트 환경
cp .env.example .env.test

# 프로덕션 환경 (나중에)
cp .env.example .env.production
```

### 데이터베이스 및 캐시 설정

#### Redis 설정
```bash
# 1. 로컬 설치
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# CentOS/RHEL
sudo yum install redis
sudo systemctl start redis

# 2. Docker 사용 (권장)
# docker-compose.yml에서 Redis 서비스 정의됨
docker-compose up redis -d

# 3. 연결 테스트
redis-cli ping
# 응답: PONG
```

#### PostgreSQL 설정 (향후 확장용)
```bash
# Docker Compose에 PostgreSQL 추가
# docker-compose.yml:
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: k_ocr
      POSTGRES_USER: k_ocr_user
      POSTGRES_PASSWORD: k_ocr_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### IDE 및 에디터 설정

#### VSCode 권장 확장 프로그램
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.flake8",
    "ms-python.black-formatter",
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-python.mypy-type-checker"
  ]
}
```

#### VSCode 설정 (.vscode/settings.json)
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "tests"
  ],
  "files.associations": {
    "*.env*": "dotenv"
  },
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm 설정
1. **인터프리터 설정**: File → Settings → Project → Python Interpreter
2. **코드 스타일**: Settings → Editor → Code Style → Python (Black 호환)
3. **런 구성**: FastAPI 서버와 Celery Worker 구성 생성

## 🧪 개발 워크플로우

### 1. 브랜치 전략
```bash
# 메인 브랜치에서 시작
git checkout main
git pull origin main

# 새 기능 브랜치 생성
git checkout -b feature/new-feature-name

# 개발 완료 후
git add .
git commit -m "feat: 새 기능 구현"
git push origin feature/new-feature-name

# PR 생성 후 메인으로 머지
```

### 2. 코드 품질 관리
```bash
# 코드 포맷팅
black backend/ tests/ --line-length 88

# 린트 검사
flake8 backend/ tests/ --max-line-length=88 --extend-ignore=E203,W503

# 타입 체킹
mypy backend/ --ignore-missing-imports

# 전체 품질 검사 스크립트
./scripts/quality-check.sh
```

### 3. 테스트 실행
```bash
# 전체 테스트 실행
pytest

# 커버리지와 함께 테스트
pytest --cov=backend --cov-report=html --cov-report=term

# 특정 모듈 테스트
pytest tests/test_core/

# 특정 테스트 케이스
pytest tests/test_core/test_ocr_engine.py::TestOCREngine::test_paddleocr_recognition

# 병렬 테스트 (성능 향상)
pytest -n auto
```

### 4. 개발 서버 관리
```bash
# 개발 스크립트 생성 (scripts/dev.sh)
#!/bin/bash
set -e

echo "🚀 K-OCR 개발 서버 시작..."

# Redis 상태 확인
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis 서버를 시작합니다..."
    brew services start redis
fi

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "가상환경을 활성화해주세요: source venv/bin/activate"
    exit 1
fi

# 의존성 설치 확인
pip install -r requirements.txt -q

# 환경 변수 로드
export $(cat .env | xargs)

# 백그라운드로 Celery Worker 시작
celery -A backend.core.tasks worker --loglevel=info &
CELERY_PID=$!

# FastAPI 서버 시작
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 정리
kill $CELERY_PID 2>/dev/null || true
```

### 5. 핫 리로드 설정
```python
# backend/main.py에서 개발용 설정
import os
from fastapi import FastAPI

app = FastAPI(
    title="K-OCR Web Corrector",
    description="한국어 문서 OCR 및 교정 웹 서비스",
    version="1.0.0",
    debug=os.getenv("DEBUG", "false").lower() == "true"
)

# 개발용 미들웨어
if app.debug:
    @app.middleware("http")
    async def add_cors_header(request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
```

## 🐳 Docker 개발 환경

### Docker Compose 사용
```bash
# 전체 스택 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up web worker redis

# 로그 확인
docker-compose logs -f web

# 컨테이너 내부 접속
docker-compose exec web bash
```

### 개발용 docker-compose.override.yml
```yaml
version: '3.8'

services:
  web:
    volumes:
      - ./backend:/app/backend:delegated
      - ./frontend:/app/frontend:delegated
      - ./tests:/app/tests:delegated
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  worker:
    volumes:
      - ./backend:/app/backend:delegated
    command: celery -A backend.core.tasks worker --loglevel=debug

  redis:
    ports:
      - "6379:6379"
```

## 🔧 고급 개발 설정

### 1. Pre-commit Hooks
```bash
# pre-commit 설치
pip install pre-commit

# .pre-commit-config.yaml 생성
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

# 훅 설치
pre-commit install
```

### 2. 환경별 설정 관리
```python
# backend/config/settings.py
from pydantic import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # 환경 설정
    environment: str = "development"
    debug: bool = False

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    # 데이터베이스 설정
    redis_url: str = "redis://localhost:6379/0"

    # 파일 저장 설정
    temp_storage_path: str = "./temp_storage"
    max_file_size: int = 52428800  # 50MB
    file_retention_hours: int = 24

    # OCR 설정
    default_ocr_engine: str = "paddleocr"
    default_dpi: int = 300

    # 보안 설정
    secret_key: str = "change-in-production"
    cors_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False

# 전역 설정 인스턴스
settings = Settings()
```

### 3. 개발용 데이터베이스 시드
```python
# scripts/seed_data.py
import asyncio
from backend.utils.temp_storage import TempStorage
from pathlib import Path

async def create_test_data():
    """테스트용 데이터 생성"""
    temp_storage = TempStorage()

    # 테스트 PDF 파일들
    test_files = Path("tests/fixtures")
    for pdf_file in test_files.glob("*.pdf"):
        with open(pdf_file, "rb") as f:
            file_id = temp_storage.save_file(
                f.read(),
                pdf_file.name,
                "application/pdf"
            )
            print(f"생성됨: {pdf_file.name} -> {file_id}")

if __name__ == "__main__":
    asyncio.run(create_test_data())
```

### 4. 성능 프로파일링
```python
# backend/utils/profiler.py
import cProfile
import pstats
from functools import wraps
from fastapi import Request
import time

def profile_endpoint(func):
    """엔드포인트 성능 프로파일링 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if os.getenv("ENABLE_PROFILING", "false").lower() == "true":
            pr = cProfile.Profile()
            pr.enable()

            result = await func(*args, **kwargs)

            pr.disable()
            stats = pstats.Stats(pr)
            stats.sort_stats('cumulative')
            stats.print_stats(10)  # 상위 10개 함수

            return result
        else:
            return await func(*args, **kwargs)

    return wrapper

# 사용 예시
@router.post("/upload")
@profile_endpoint
async def upload_file(file: UploadFile):
    # 구현...
```

## 📊 개발 모니터링

### 1. 로그 설정
```python
# backend/utils/logging_config.py
import logging.config
import os

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/app.log",
        },
    },
    "loggers": {
        "backend": {
            "level": "DEBUG" if os.getenv("DEBUG") == "true" else "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### 2. 헬스체크 엔드포인트 확장
```python
@app.get("/health/detailed")
async def detailed_health_check():
    """상세 헬스체크"""
    import redis
    import psutil

    redis_status = "healthy"
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow(),
        "services": {
            "redis": redis_status,
            "disk_usage": psutil.disk_usage("/").percent,
            "memory_usage": psutil.virtual_memory().percent,
        },
        "version": "1.0.0"
    }
```

## 🎯 개발 팁과 모범 사례

### 1. 효율적인 개발 환경
```bash
# 유용한 별칭 설정 (~/.bashrc 또는 ~/.zshrc)
alias k-ocr-dev="cd ~/Projects/AutoOCR && source venv/bin/activate"
alias k-ocr-test="pytest --cov=backend --cov-report=term-missing"
alias k-ocr-lint="black backend/ tests/ && flake8 backend/ tests/"
alias k-ocr-server="uvicorn backend.main:app --reload"
alias k-ocr-worker="celery -A backend.core.tasks worker --loglevel=info"
```

### 2. VSCode 작업 공간 설정
```json
{
  "folders": [
    {
      "name": "K-OCR Backend",
      "path": "./backend"
    },
    {
      "name": "K-OCR Frontend",
      "path": "./frontend"
    },
    {
      "name": "K-OCR Tests",
      "path": "./tests"
    }
  ],
  "settings": {
    "python.defaultInterpreterPath": "./venv/bin/python"
  }
}
```

### 3. 디버깅 설정
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Server",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/venv/bin/uvicorn",
      "args": [
        "backend.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    },
    {
      "name": "Celery Worker",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/venv/bin/celery",
      "args": [
        "-A", "backend.core.tasks",
        "worker",
        "--loglevel=debug"
      ],
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}"
    }
  ]
}
```

## 🆘 트러블슈팅

### 일반적인 문제들

#### 1. 의존성 설치 오류
```bash
# 문제: pip install 실패
# 해결: pip 업그레이드 후 재시도
python -m pip install --upgrade pip
pip install -r requirements.txt

# macOS에서 cryptography 설치 오류
export LDFLAGS=-L$(brew --prefix libffi)/lib
export CPPFLAGS=-I$(brew --prefix libffi)/include
pip install cryptography
```

#### 2. Redis 연결 오류
```bash
# Redis 서비스 상태 확인
redis-cli ping

# Redis 재시작
brew services restart redis  # macOS
sudo systemctl restart redis  # Linux
```

#### 3. 포트 충돌
```bash
# 포트 사용 확인
lsof -i :8000
lsof -i :6379

# 프로세스 종료
kill -9 [PID]
```

#### 4. 환경변수 로드 안됨
```bash
# .env 파일 위치 확인
ls -la .env

# 환경변수 수동 로드
export $(cat .env | xargs)
```

### 성능 최적화 팁

#### 1. 개발용 성능 향상
```bash
# Python 최적화 플래그
export PYTHONOPTIMIZE=1

# 개발 서버 워커 수 조정
uvicorn backend.main:app --workers 4 --reload
```

#### 2. 메모리 사용량 모니터링
```python
import psutil
import threading
import time

def memory_monitor():
    """메모리 사용량 모니터링"""
    while True:
        memory = psutil.virtual_memory()
        print(f"Memory usage: {memory.percent}%")
        if memory.percent > 80:
            print("⚠️  높은 메모리 사용량 감지!")
        time.sleep(10)

# 개발 중 백그라운드 실행
threading.Thread(target=memory_monitor, daemon=True).start()
```

---

**마지막 업데이트**: 2024년 1월
**대상 독자**: 백엔드/풀스택 개발자
**난이도**: 초급 ~ 중급