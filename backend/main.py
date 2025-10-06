"""
K-OCR Web Corrector - FastAPI Main Application
한국어 문서 OCR 및 교정 웹 서비스의 메인 애플리케이션
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

# API 라우터 임포트
from backend.api import upload, processing, download

# 필수 디렉토리 생성 (시작 시) - Dockerfile에서 생성되므로 확인만 수행
BASE_DIR = Path(__file__).parent.parent
REQUIRED_DIRS = [
    BASE_DIR / "temp_storage",
    BASE_DIR / "logs",
    BASE_DIR / "processed_images",
    BASE_DIR / "temp_images"
]

for directory in REQUIRED_DIRS:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o775)
    except PermissionError:
        # Dockerfile에서 이미 생성되었으므로 무시
        pass
    except Exception as e:
        # 기타 에러는 로깅만 하고 계속 진행
        import logging
        logging.warning(f"Could not create/modify directory {directory}: {e}")

app = FastAPI(
    title="K-OCR Web Corrector",
    description="한국어 문서 OCR 및 교정 웹 서비스",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서만 사용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
STATIC_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "K-OCR Web Corrector",
        "version": "1.0.0"
    }


# API 라우터 등록
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(processing.router, prefix="/api", tags=["processing"])
app.include_router(download.router, prefix="/api", tags=["download"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )