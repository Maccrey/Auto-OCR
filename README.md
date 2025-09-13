# K-OCR Web Corrector

한국어 문서 OCR 및 교정 웹 서비스

## 프로젝트 개요

K-OCR Web Corrector는 PDF 문서를 웹을 통해 업로드하여 PNG로 변환 후, 이미지 전처리 및 OCR 처리를 거쳐 한국어 텍스트 파일로 다운로드할 수 있는 웹 애플리케이션입니다.

### 핵심 기능

- **웹 기반 인터페이스**: 브라우저만으로 접근 가능
- **PDF to PNG 변환**: 고품질 이미지 변환
- **이미지 전처리**: 흑백변환, 대비조정, 기울기보정, 노이즈제거
- **한국어 OCR**: PaddleOCR 및 Tesseract 엔진 지원
- **텍스트 교정**: 띄어쓰기 및 맞춤법 자동 교정
- **비동기 처리**: Celery와 Redis를 활용한 백그라운드 작업
- **실시간 진행률**: 처리 상태 실시간 표시

## 아키텍처

```
Frontend (HTML/CSS/JS) → FastAPI → Celery Workers → OCR Engine
                                      ↓
                                   Redis Queue
                                      ↓
                              Processing Pipeline
```

### 기술 스택

#### Backend
- **FastAPI**: 웹 프레임워크
- **Celery**: 비동기 작업 처리
- **Redis**: 메시지 브로커 및 캐시
- **PyMuPDF**: PDF 처리
- **OpenCV**: 이미지 전처리
- **PaddleOCR**: 한국어 OCR 엔진
- **Tesseract**: 보조 OCR 엔진

#### Frontend
- **HTML5/CSS3**: 사용자 인터페이스
- **JavaScript**: 클라이언트 로직
- **Jinja2**: 템플릿 엔진

#### DevOps
- **Docker**: 컨테이너화
- **Docker Compose**: 개발 환경
- **pytest**: 테스트 프레임워크

## 설치 및 실행

### 요구사항

- Python 3.9+
- Redis
- Docker (선택사항)

### 로컬 개발 환경

1. **저장소 클론**
   ```bash
   git clone <repository-url>
   cd AutoOCR
   ```

2. **가상환경 설정**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

4. **환경변수 설정**
   ```bash
   cp .env.example .env
   # .env 파일을 편집하여 필요한 설정값 입력
   ```

5. **Redis 서버 실행**
   ```bash
   redis-server
   ```

6. **Celery Worker 실행** (별도 터미널)
   ```bash
   celery -A backend.core.tasks worker --loglevel=info
   ```

7. **FastAPI 개발 서버 실행** (별도 터미널)
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **웹 브라우저에서 접속**
   ```
   http://localhost:8000
   ```

### Docker를 사용한 실행

1. **개발 환경 실행**
   ```bash
   docker-compose up --build
   ```

2. **백그라운드 실행**
   ```bash
   docker-compose up -d
   ```

3. **로그 확인**
   ```bash
   docker-compose logs -f
   ```

4. **컨테이너 정지**
   ```bash
   docker-compose down
   ```

## 개발

### 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 커버리지와 함께 테스트 실행
pytest --cov=backend --cov-report=html

# 특정 모듈 테스트
pytest tests/test_core/
```

### 코드 품질 검사

```bash
# 코드 포맷팅
black backend/ tests/

# 린트 검사
flake8 backend/ tests/

# 타입 체킹
mypy backend/
```

### 디렉토리 구조

```
AutoOCR/
├── backend/
│   ├── api/                    # FastAPI 라우터들
│   │   ├── upload.py          # 파일 업로드 API
│   │   ├── processing.py      # 처리 상태 API
│   │   └── download.py        # 결과 다운로드 API
│   ├── core/                  # 핵심 비즈니스 로직
│   │   ├── pdf_converter.py   # PDF → PNG 변환
│   │   ├── image_processor.py # 이미지 전처리
│   │   ├── ocr_engine.py      # OCR 엔진 관리
│   │   ├── text_corrector.py  # 텍스트 교정
│   │   ├── file_generator.py  # 결과 파일 생성
│   │   └── tasks.py          # Celery 태스크 정의
│   ├── utils/                 # 유틸리티 모듈
│   │   ├── temp_storage.py    # 임시 파일 관리
│   │   ├── config_manager.py  # 설정 관리
│   │   └── file_handler.py    # 파일 처리 유틸
│   └── main.py               # FastAPI 애플리케이션 진입점
├── frontend/
│   ├── static/               # 정적 파일들
│   └── templates/            # Jinja2 템플릿
├── tests/                    # 테스트 파일들
├── temp_storage/            # 임시 파일 저장소
└── config/                  # 설정 파일들
```

## API 문서

개발 서버 실행 후 다음 URL에서 자동 생성된 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 사용법

1. **PDF 파일 업로드**: 웹 인터페이스에서 PDF 파일을 드래그 앤 드롭 또는 클릭하여 업로드
2. **처리 옵션 설정**: 이미지 전처리 및 OCR 옵션 선택
3. **처리 시작**: 업로드 완료 후 자동으로 처리 시작
4. **진행률 확인**: 실시간으로 처리 진행률 확인
5. **결과 다운로드**: 처리 완료 후 텍스트 파일 다운로드

## 개발 진행 상황

### ✅ 완료된 모듈
- **TempStorage**: 임시 파일 관리 (16개 테스트 통과)
- **PDFConverter**: PDF to PNG 변환 (19개 테스트 통과)
- **ImageProcessor**: 이미지 전처리 (20개 테스트 통과)

### 🚧 개발 중
- **OCREngine**: OCR 엔진 관리
- **TextCorrector**: 텍스트 교정
- **FileGenerator**: 결과 파일 생성
- **Web API**: RESTful API 엔드포인트
- **Frontend**: 사용자 인터페이스

## 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 개발 가이드라인

- **TDD 방식**: 테스트 먼저 작성 후 구현
- **코드 커버리지**: 85% 이상 유지
- **타입 힌트**: 모든 함수에 타입 힌트 적용
- **PEP 8**: Black 포매터 사용
- **Docstring**: Google 스타일 문서화

## 라이선스

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 문의

프로젝트 관련 문의사항이나 버그 리포트는 [Issues](https://github.com/username/AutoOCR/issues)에 등록해 주세요.

## 감사의 말

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - 뛰어난 한국어 OCR 성능
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - 오픈소스 OCR 엔진
- [FastAPI](https://fastapi.tiangolo.com/) - 현대적인 웹 프레임워크
- [OpenCV](https://opencv.org/) - 강력한 이미지 처리 라이브러리