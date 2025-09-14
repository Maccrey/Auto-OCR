#!/usr/bin/env python3
"""
OCR 모델 다운로드 및 캐싱 스크립트

이 스크립트는 Docker 빌드 시 OCR 모델을 미리 다운로드하여
컨테이너 시작 시간을 단축합니다.
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_paddleocr_models(lang: str = 'korean') -> bool:
    """PaddleOCR 모델 다운로드"""
    try:
        logger.info(f"PaddleOCR {lang} 모델 다운로드 시작...")

        import paddleocr

        # PaddleOCR 인스턴스 생성 (모델 자동 다운로드)
        ocr = paddleocr.PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            show_log=False,
            use_gpu=False  # CPU 버전 사용
        )

        # 모델 위치 확인
        home = os.path.expanduser('~')
        paddle_dir = Path(home) / '.paddleocr'

        if paddle_dir.exists():
            logger.info(f"PaddleOCR 모델 다운로드 완료: {paddle_dir}")

            # 다운로드된 파일 크기 확인
            total_size = sum(
                f.stat().st_size for f in paddle_dir.rglob('*') if f.is_file()
            )
            logger.info(f"다운로드된 모델 크기: {total_size / (1024*1024):.1f} MB")

            return True
        else:
            logger.warning("PaddleOCR 모델 디렉토리를 찾을 수 없음")
            return False

    except Exception as e:
        logger.error(f"PaddleOCR 모델 다운로드 실패: {e}")
        return False


def download_tesseract_data() -> bool:
    """Tesseract 언어 데이터 확인"""
    try:
        logger.info("Tesseract 언어 데이터 확인...")

        import pytesseract

        # Tesseract 설정 확인
        langs = pytesseract.get_languages(config='')
        logger.info(f"사용 가능한 Tesseract 언어: {langs}")

        if 'kor' in langs:
            logger.info("Tesseract 한국어 데이터 사용 가능")
            return True
        else:
            logger.warning("Tesseract 한국어 데이터가 설치되지 않음")
            return False

    except Exception as e:
        logger.error(f"Tesseract 데이터 확인 실패: {e}")
        return False


def setup_model_cache_directory(cache_dir: Optional[str] = None) -> Path:
    """모델 캐시 디렉토리 설정"""
    if cache_dir:
        model_dir = Path(cache_dir)
    else:
        model_dir = Path('/app/models')

    model_dir.mkdir(parents=True, exist_ok=True)

    # 하위 디렉토리 생성
    (model_dir / 'paddleocr').mkdir(exist_ok=True)
    (model_dir / 'tesseract').mkdir(exist_ok=True)

    logger.info(f"모델 캐시 디렉토리 설정: {model_dir}")
    return model_dir


def copy_models_to_cache(model_dir: Path) -> bool:
    """다운로드된 모델을 캐시 디렉토리로 복사"""
    try:
        import shutil

        # PaddleOCR 모델 복사
        home = os.path.expanduser('~')
        paddle_source = Path(home) / '.paddleocr'
        paddle_dest = model_dir / 'paddleocr'

        if paddle_source.exists():
            logger.info(f"PaddleOCR 모델 복사: {paddle_source} -> {paddle_dest}")
            shutil.copytree(paddle_source, paddle_dest, dirs_exist_ok=True)

        return True

    except Exception as e:
        logger.error(f"모델 복사 실패: {e}")
        return False


def verify_models(model_dir: Path) -> bool:
    """모델 파일 검증"""
    try:
        logger.info("모델 파일 검증...")

        paddle_dir = model_dir / 'paddleocr'
        if paddle_dir.exists():
            files = list(paddle_dir.rglob('*.pdmodel'))
            logger.info(f"PaddleOCR 모델 파일 수: {len(files)}")

            for file in files[:3]:  # 처음 3개만 표시
                logger.info(f"  - {file.relative_to(model_dir)}")

        return True

    except Exception as e:
        logger.error(f"모델 검증 실패: {e}")
        return False


def main():
    """메인 함수"""
    logger.info("OCR 모델 다운로드 스크립트 시작")

    # 환경변수에서 설정 읽기
    lang = os.getenv('PADDLE_LANG', 'korean')
    cache_dir = os.getenv('MODEL_CACHE_DIR')

    # 모델 캐시 디렉토리 설정
    model_dir = setup_model_cache_directory(cache_dir)

    success_count = 0
    total_count = 2

    # PaddleOCR 모델 다운로드
    if download_paddleocr_models(lang):
        success_count += 1

    # Tesseract 데이터 확인
    if download_tesseract_data():
        success_count += 1

    # 모델을 캐시 디렉토리로 복사
    if copy_models_to_cache(model_dir):
        logger.info("모델 캐싱 완료")

    # 모델 검증
    verify_models(model_dir)

    # 결과 출력
    logger.info(f"모델 다운로드 완료: {success_count}/{total_count}")

    if success_count == total_count:
        logger.info("모든 모델이 성공적으로 다운로드되었습니다")
        sys.exit(0)
    else:
        logger.warning("일부 모델 다운로드에 실패했습니다")
        sys.exit(1)


if __name__ == '__main__':
    main()