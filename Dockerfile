# Multi-stage build for K-OCR Web Corrector Production
# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# 메타데이터 라벨
LABEL maintainer="K-OCR Web Corrector Team"
LABEL version="1.0.0"
LABEL description="Korean OCR Web Service with PDF processing"

# 시스템 패키지 설치 (캐시 최적화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OCR 엔진
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    # OpenCV 의존성 (Debian 12+ 호환)
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    # PDF 처리
    libfontconfig1 \
    libfreetype6 \
    # 네트워킹 및 유틸리티
    wget \
    curl \
    git \
    # 빌드 도구 (임시)
    build-essential \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Python 환경 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Stage 2: Dependencies installation
FROM base as dependencies

# Python 의존성 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# OCR 모델 다운로드 및 캐싱
RUN python -c "import paddleocr; import os; \
print('PaddleOCR 한국어 모델 다운로드 중...'); \
ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang='korean', show_log=False); \
print('PaddleOCR 모델 다운로드 완료'); \
home = os.path.expanduser('~'); \
paddle_dir = os.path.join(home, '.paddleocr'); \
print(f'PaddleOCR 모델 위치: {paddle_dir}') if os.path.exists(paddle_dir) else None" \
    || echo "PaddleOCR 모델 다운로드 실패 - 런타임에 다운로드됩니다"

# 빌드 도구 정리
RUN apt-get remove -y build-essential pkg-config && \
    apt-get autoremove -y && \
    apt-get clean

# Stage 3: Application
FROM dependencies as app

# 비-root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 애플리케이션 디렉토리 및 권한 설정
RUN mkdir -p /app/temp_storage /app/logs /app/models && \
    chown -R appuser:appuser /app

# 애플리케이션 코드 복사
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser frontend/ ./frontend/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser .env.example ./.env

# PaddleOCR 모델 복사 (만약 설치되었다면)
RUN if [ -d "/root/.paddleocr" ]; then \
        cp -r /root/.paddleocr /app/models/paddleocr && \
        chown -R appuser:appuser /app/models/paddleocr; \
    fi

# Stage 4: Development
FROM dependencies as development

ENV ENVIRONMENT=development

# 개발용 추가 패키지 설치
RUN pip install --no-cache-dir \
    ipython \
    ipdb \
    pytest-watch \
    python-dotenv

# 애플리케이션 코드 복사 (개발용)
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY config/ ./config/
COPY .env.example ./.env

# 개발용 디렉토리 생성
RUN mkdir -p temp_storage logs

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/download/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Stage 5: Worker (Celery)
FROM app as worker

ENV ENVIRONMENT=production \
    CELERY_BROKER_URL=redis://redis:6379/0 \
    CELERY_RESULT_BACKEND=redis://redis:6379/0

USER appuser

# Celery 워커 시작 명령
CMD ["celery", "-A", "backend.core.tasks", "worker", "--loglevel=info", "--concurrency=4"]

# Stage 6: Scheduler (Celery Beat)
FROM app as scheduler

ENV ENVIRONMENT=production \
    CELERY_BROKER_URL=redis://redis:6379/0 \
    CELERY_RESULT_BACKEND=redis://redis:6379/0

USER appuser

# Celery Beat 스케줄러 시작 명령
CMD ["celery", "-A", "backend.core.tasks", "beat", "--loglevel=info"]

# Stage 7: Production (Default)
FROM app as production

ENV ENVIRONMENT=production \
    WORKERS=4 \
    MAX_WORKERS=8 \
    TIMEOUT=300 \
    KEEP_ALIVE=2

# 디렉토리 권한 설정 (USER 변경 전에 실행)
RUN touch /app/logs/app.log && \
    chmod 664 /app/logs/app.log && \
    chmod 775 /app/temp_storage && \
    chmod 775 /app/logs

# 보안 설정
USER appuser

# 헬스체크 설정
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/download/health || exit 1

EXPOSE 8000

# 프로덕션 시작 명령 (단일 워커로 시작 - 메모리 절약)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "5"]