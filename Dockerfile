# Multi-stage build for K-OCR Web Corrector
FROM python:3.9-slim as base

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-kor \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# PaddleOCR 한국어 모델 다운로드를 위한 준비
ENV PYTHONPATH=/app
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY config/ ./config/

# 임시 저장소 디렉토리 생성
RUN mkdir -p temp_storage

# 개발 단계
FROM base as development
ENV ENVIRONMENT=development
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 프로덕션 단계
FROM base as production
ENV ENVIRONMENT=production
EXPOSE 8000

# 비-root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]