"""
프론트엔드 API 모듈

이 모듈은 웹 프론트엔드 페이지를 서빙하는 API 엔드포인트를 제공합니다:
- GET /: 메인 페이지
- 정적 파일 서빙 (CSS, JS, 이미지)
"""

import os
import logging
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(tags=["frontend"])

# 템플릿 디렉토리 설정
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    """
    메인 페이지 렌더링

    Args:
        request: FastAPI Request 객체

    Returns:
        HTMLResponse: 렌더링된 메인 페이지

    Raises:
        HTTPException: 템플릿 로딩 실패 시
    """
    try:
        # 페이지 컨텍스트 데이터
        context = {
            "request": request,
            "title": "K-OCR Web Corrector",
            "description": "한국어 문서 OCR 및 교정 웹 서비스",
            "version": "1.0.0",
            "max_file_size": 50,  # MB
            "supported_formats": ["PDF"],
            "features": {
                "ocr_engines": [
                    {"id": "paddle", "name": "PaddleOCR", "description": "한국어 최적화"},
                    {"id": "tesseract", "name": "Tesseract", "description": "범용 OCR"},
                    {"id": "ensemble", "name": "앙상블", "description": "높은 정확도"}
                ],
                "preprocessing": [
                    {"id": "clahe", "name": "대비 향상", "enabled": True},
                    {"id": "deskew", "name": "기울기 보정", "enabled": True},
                    {"id": "noise", "name": "노이즈 제거", "enabled": True}
                ],
                "correction": [
                    {"id": "spacing", "name": "띄어쓰기 교정", "enabled": True},
                    {"id": "spelling", "name": "맞춤법 교정", "enabled": True}
                ]
            },
            "settings": {
                "default_dpi": 300,
                "default_language": "ko",
                "max_pages": 100
            }
        }

        logger.info("Main page requested")
        return templates.TemplateResponse("index.html", context)

    except Exception as e:
        logger.error(f"Failed to render main page: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load main page"
        )


@router.get("/health")
async def frontend_health_check():
    """
    프론트엔드 서비스 헬스체크

    Returns:
        Dict: 서비스 상태 정보
    """
    try:
        # 템플릿 디렉토리 존재 확인
        template_exists = TEMPLATE_DIR.exists() and (TEMPLATE_DIR / "index.html").exists()

        # 정적 파일 디렉토리 확인
        static_dir = TEMPLATE_DIR.parent / "static"
        static_exists = static_dir.exists()

        status = "healthy" if template_exists and static_exists else "degraded"

        return {
            "status": status,
            "components": {
                "templates": "available" if template_exists else "missing",
                "static_files": "available" if static_exists else "missing"
            },
            "template_dir": str(TEMPLATE_DIR),
            "static_dir": str(static_dir)
        }

    except Exception as e:
        logger.error(f"Frontend health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/api-info")
async def get_api_info():
    """
    API 정보 제공 (프론트엔드에서 사용)

    Returns:
        Dict: API 엔드포인트 정보
    """
    return {
        "endpoints": {
            "upload": "/api/upload",
            "processing": "/api/process",
            "download": "/api/download",
            "status": "/api/upload/{upload_id}/status"
        },
        "limits": {
            "max_file_size": 50 * 1024 * 1024,  # 50MB in bytes
            "allowed_formats": [".pdf"],
            "max_pages": 100
        },
        "features": {
            "ocr_engines": ["paddle", "tesseract", "ensemble"],
            "languages": ["ko", "ko+en"],
            "preprocessing": ["clahe", "deskew", "noise_removal"],
            "correction": ["spacing", "spelling"]
        }
    }


# 에러 페이지들
@router.get("/error/{error_code}", response_class=HTMLResponse)
async def error_page(request: Request, error_code: int):
    """
    에러 페이지 렌더링

    Args:
        request: FastAPI Request 객체
        error_code: HTTP 에러 코드

    Returns:
        HTMLResponse: 에러 페이지
    """
    try:
        error_messages = {
            404: {
                "title": "페이지를 찾을 수 없습니다",
                "message": "요청하신 페이지가 존재하지 않습니다.",
                "suggestion": "메인 페이지로 돌아가서 다시 시도해보세요."
            },
            500: {
                "title": "서버 오류가 발생했습니다",
                "message": "일시적인 서버 오류가 발생했습니다.",
                "suggestion": "잠시 후 다시 시도해보세요."
            },
            503: {
                "title": "서비스 점검 중입니다",
                "message": "현재 서비스 점검 중입니다.",
                "suggestion": "점검 완료 후 이용해주세요."
            }
        }

        error_info = error_messages.get(error_code, {
            "title": "오류가 발생했습니다",
            "message": f"오류 코드: {error_code}",
            "suggestion": "메인 페이지로 돌아가서 다시 시도해보세요."
        })

        context = {
            "request": request,
            "error_code": error_code,
            "error_title": error_info["title"],
            "error_message": error_info["message"],
            "error_suggestion": error_info["suggestion"]
        }

        # 에러 페이지 템플릿이 있다면 사용, 없다면 기본 메시지
        try:
            return templates.TemplateResponse("error.html", context)
        except:
            # 에러 페이지 템플릿이 없는 경우 간단한 HTML 반환
            html_content = f"""
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{error_info['title']} - K-OCR Web Corrector</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex; align-items: center; justify-content: center;
                        min-height: 100vh; margin: 0; background: #f5f5f5;
                    }}
                    .error-container {{
                        text-align: center; background: white; padding: 2rem;
                        border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        max-width: 500px;
                    }}
                    h1 {{ color: #e74c3c; margin-bottom: 1rem; }}
                    p {{ color: #666; margin-bottom: 1rem; }}
                    a {{
                        background: #3498db; color: white; text-decoration: none;
                        padding: 0.75rem 1.5rem; border-radius: 4px; display: inline-block;
                    }}
                    a:hover {{ background: #2980b9; }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>{error_code}</h1>
                    <h2>{error_info['title']}</h2>
                    <p>{error_info['message']}</p>
                    <p>{error_info['suggestion']}</p>
                    <a href="/">메인 페이지로 돌아가기</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=error_code)

    except Exception as e:
        logger.error(f"Failed to render error page: {e}")
        return HTMLResponse(
            content=f"<h1>Error {error_code}</h1><p>An error occurred while rendering the error page.</p>",
            status_code=error_code
        )