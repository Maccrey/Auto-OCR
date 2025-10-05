# K-OCR Web Corrector - Cloudtype 배포 가이드

이 문서는 K-OCR Web Corrector를 Cloudtype 플랫폼에 배포하는 방법을 안내합니다.

---

## 📋 목차

- [Cloudtype 소개](#cloudtype-소개)
- [사전 준비사항](#사전-준비사항)
- [배포 방법](#배포-방법)
  - [1. GitHub 연동 배포](#1-github-연동-배포)
  - [2. Docker 이미지 배포](#2-docker-이미지-배포)
- [환경 변수 설정](#환경-변수-설정)
- [서비스 설정](#서비스-설정)
- [배포 후 확인사항](#배포-후-확인사항)
- [트러블슈팅](#트러블슈팅)
- [성능 최적화](#성능-최적화)

---

## Cloudtype 소개

[Cloudtype](https://cloudtype.io/)은 한국에서 개발된 PaaS(Platform as a Service)로, GitHub 저장소와 연동하여 자동으로 애플리케이션을 빌드하고 배포할 수 있습니다.

### 주요 특징
- ✅ GitHub 자동 연동 및 CI/CD
- ✅ 무료 플랜 제공 (제한적)
- ✅ Docker 이미지 지원
- ✅ 한국어 인터페이스
- ✅ 서울 리전 (빠른 응답 속도)

---

## 사전 준비사항

### 1. Cloudtype 계정 준비
- [Cloudtype 웹사이트](https://cloudtype.io/)에서 회원가입
- GitHub 계정 연동

### 2. GitHub 저장소 준비
- 프로젝트 코드가 GitHub에 푸시되어 있어야 함
- Public 또는 Private 저장소 모두 가능

### 3. 필요한 파일 확인
프로젝트 루트에 다음 파일들이 있어야 합니다:
```
AutoOCR/
├── Dockerfile              # Docker 빌드 설정
├── requirements.txt        # Python 의존성
├── backend/               # 백엔드 소스 코드
├── frontend/              # 프론트엔드 소스 코드
├── .env.example           # 환경 변수 예시
└── DEPLOY.md             # 이 파일
```

---

## 배포 방법

### 1. GitHub 연동 배포 (권장)

#### Step 1: 새 프로젝트 생성
1. Cloudtype 대시보드에서 **"새 프로젝트"** 클릭
2. **"GitHub 저장소 연동"** 선택
3. 저장소 목록에서 `AutoOCR` 선택

#### Step 2: 빌드 설정
```yaml
# Cloudtype 빌드 설정
Runtime: Docker
Dockerfile Path: ./Dockerfile
Build Context: .
Port: 8000
Start Command: (비워두기 - Dockerfile CMD 사용)
```

**⚠️ Start Command 참고:**
- **권장**: 비워두기 (Dockerfile의 CMD가 자동 실행)
- **명시 설정 시**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- **멀티워커**: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2`

#### Step 3: 서비스 이름 설정
```
서비스 이름: k-ocr-web
도메인: k-ocr-web.cloudtype.app (자동 생성)
```

#### Step 4: 리소스 선택
무료 플랜 (Free Tier):
- CPU: 0.25 vCPU
- Memory: 512 MB
- Storage: 1 GB

스타터 플랜 (Starter - 권장):
- CPU: 0.5 vCPU
- Memory: 1 GB
- Storage: 10 GB

프로 플랜 (Pro):
- CPU: 1 vCPU
- Memory: 2 GB
- Storage: 20 GB

#### Step 5: 환경 변수 설정
Cloudtype 대시보드에서 환경 변수 설정:

```bash
# 필수 환경 변수
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<랜덤한_시크릿_키_생성>
PORT=8000
HOST=0.0.0.0

# 파일 업로드 설정
MAX_FILE_SIZE=52428800
ALLOWED_EXTENSIONS=.pdf
TEMP_FILE_TTL=86400

# OCR 엔진 설정
DEFAULT_OCR_ENGINE=paddleocr
ENABLE_TESSERACT=true
ENABLE_PADDLEOCR=true
PADDLEOCR_USE_GPU=false

# 이미지 처리 설정
DEFAULT_DPI=300
ENABLE_PREPROCESSING=true

# 텍스트 교정 설정
ENABLE_SPACING_CORRECTION=false  # 라이브러리 호환성 이슈로 비활성화
ENABLE_SPELL_CORRECTION=false    # 라이브러리 호환성 이슈로 비활성화
ENABLE_CUSTOM_RULES=true

# 로깅 설정
LOG_LEVEL=INFO

# 보안 설정
CORS_ORIGINS=["https://k-ocr-web.cloudtype.app"]
TRUSTED_HOSTS=["k-ocr-web.cloudtype.app"]

# 성능 설정
WORKER_PROCESSES=2
WORKER_TIMEOUT=300
MAX_CONCURRENT_UPLOADS=5
```

**⚠️ 중요**: `SECRET_KEY`는 반드시 안전한 랜덤 문자열로 설정하세요.
```bash
# 시크릿 키 생성 예시 (로컬에서 실행)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Step 6: 배포 시작
1. **"배포하기"** 버튼 클릭
2. 빌드 로그 확인 (5~10분 소요)
3. 배포 완료 후 URL 확인

---

### 2. Docker 이미지 배포

#### Step 1: Docker 이미지 빌드
로컬에서 Docker 이미지 빌드:
```bash
# 프로젝트 루트에서 실행
docker build -t k-ocr-web:latest .
```

#### Step 2: Docker Hub에 푸시
```bash
# Docker Hub 로그인
docker login

# 이미지 태그 설정
docker tag k-ocr-web:latest <your-dockerhub-username>/k-ocr-web:latest

# 이미지 푸시
docker push <your-dockerhub-username>/k-ocr-web:latest
```

#### Step 3: Cloudtype에서 배포
1. Cloudtype 대시보드에서 **"새 프로젝트"** 클릭
2. **"Docker 이미지"** 선택
3. 이미지 이름 입력: `<your-dockerhub-username>/k-ocr-web:latest`
4. 포트 설정: `8000`
5. 환경 변수 설정 (위와 동일)
6. **"배포하기"** 클릭

---

## 환경 변수 설정

### 필수 환경 변수

| 변수명 | 설명 | 기본값 | 프로덕션 권장값 |
|--------|------|--------|----------------|
| `ENVIRONMENT` | 실행 환경 | `development` | `production` |
| `DEBUG` | 디버그 모드 | `true` | `false` |
| `SECRET_KEY` | 암호화 키 | - | 랜덤 생성 필수 |
| `PORT` | 서버 포트 | `8000` | `8000` |
| `HOST` | 바인딩 주소 | `0.0.0.0` | `0.0.0.0` |

### 선택적 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `MAX_FILE_SIZE` | 최대 업로드 크기 (bytes) | `52428800` (50MB) |
| `TEMP_FILE_TTL` | 임시 파일 보관 시간 (초) | `86400` (24시간) |
| `DEFAULT_OCR_ENGINE` | 기본 OCR 엔진 | `paddleocr` |
| `DEFAULT_DPI` | PDF → PNG 변환 DPI | `300` |
| `WORKER_PROCESSES` | 워커 프로세스 수 | `2` |
| `WORKER_TIMEOUT` | 워커 타임아웃 (초) | `300` |
| `MAX_CONCURRENT_UPLOADS` | 동시 업로드 제한 | `10` |

### 보안 관련 환경 변수

```bash
# CORS 설정 (배포 URL로 변경 필요)
CORS_ORIGINS=["https://your-app.cloudtype.app"]

# 신뢰할 수 있는 호스트
TRUSTED_HOSTS=["your-app.cloudtype.app"]
```

---

## 서비스 설정

### Cloudtype 프로젝트 설정 파일

프로젝트 루트에 `.cloudtype/config.yaml` 생성 (선택사항):

```yaml
name: k-ocr-web
type: web

build:
  dockerfile: Dockerfile
  context: .

ports:
  - 8000

env:
  - name: ENVIRONMENT
    value: production
  - name: PORT
    value: "8000"
  - name: PYTHONUNBUFFERED
    value: "1"

resources:
  cpu: 0.5
  memory: 1024

healthcheck:
  path: /health
  interval: 30s
  timeout: 10s
  retries: 3

autoscaling:
  enabled: false  # 무료 플랜에서는 비활성화
  min: 1
  max: 3
  targetCPU: 70
```

---

## 배포 후 확인사항

### 1. 헬스 체크
배포 완료 후 서비스 상태 확인:

```bash
# 헬스 체크 엔드포인트 호출
curl https://your-app.cloudtype.app/health

# 응답 예시
{
  "status": "healthy",
  "service": "K-OCR Web Corrector",
  "version": "1.0.0"
}
```

### 2. API 문서 확인
자동 생성된 API 문서 접근:
- Swagger UI: `https://your-app.cloudtype.app/api/docs`
- ReDoc: `https://your-app.cloudtype.app/api/redoc`

### 3. 기본 기능 테스트

#### 웹 인터페이스 접속
```
https://your-app.cloudtype.app/
```

#### 파일 업로드 테스트
1. 메인 페이지에서 PDF 파일 업로드
2. 처리 진행률 확인
3. 결과 다운로드 테스트

#### API 테스트 (curl)
```bash
# 파일 업로드 테스트
curl -X POST https://your-app.cloudtype.app/api/upload \
  -F "file=@test.pdf" \
  -H "Content-Type: multipart/form-data"

# 응답에서 upload_id 확인 후 상태 조회
curl https://your-app.cloudtype.app/api/upload/{upload_id}/status
```

### 4. 로그 확인
Cloudtype 대시보드에서:
1. 프로젝트 선택
2. **"로그"** 탭 클릭
3. 실시간 로그 모니터링

---

## 트러블슈팅

### 1. 빌드 실패

#### 문제: "Dockerfile not found"
```bash
# 해결책: Dockerfile 경로 확인
ls -la Dockerfile
```

#### 문제: "requirements.txt not found"
```bash
# 해결책: requirements.txt 파일 확인
ls -la requirements.txt
```

#### 문제: "Python 패키지 설치 실패"
```yaml
# 해결책: requirements.txt에서 호환되지 않는 패키지 제거
# kospacing, py-hanspell은 Python 3.13에서 호환성 이슈
# 해당 라인을 주석 처리하거나 제거
```

### 2. 런타임 오류

#### 문제: "502 Bad Gateway"
원인:
- 애플리케이션이 시작되지 않음
- 포트 설정 오류

해결책:
```bash
# 1. 환경 변수 PORT 확인
PORT=8000

# 2. 애플리케이션이 0.0.0.0에서 리스닝하는지 확인
HOST=0.0.0.0

# 3. Cloudtype 로그에서 에러 메시지 확인
```

#### 문제: "Out of Memory"
원인:
- 메모리 부족 (무료 플랜: 512MB)
- PaddleOCR 모델 로딩 시 메모리 많이 사용

해결책:
```bash
# 1. 플랜 업그레이드 (1GB 이상 권장)
# 2. 환경 변수 조정
PADDLEOCR_USE_GPU=false
MAX_CONCURRENT_UPLOADS=3  # 동시 처리 수 감소
```

#### 문제: "Timeout Error"
원인:
- OCR 처리 시간이 너무 오래 걸림
- 워커 타임아웃 초과

해결책:
```bash
# 환경 변수 조정
WORKER_TIMEOUT=600  # 10분으로 증가
```

### 3. 파일 업로드 오류

#### 문제: "File too large"
```bash
# 해결책: MAX_FILE_SIZE 조정 (50MB 기본값)
MAX_FILE_SIZE=104857600  # 100MB
```

#### 문제: "Invalid file type"
```bash
# 해결책: ALLOWED_EXTENSIONS 확인
ALLOWED_EXTENSIONS=.pdf
```

### 4. OCR 품질 문제

#### 문제: "OCR 정확도가 낮음"
해결책:
```bash
# 1. DPI 증가 (더 선명한 이미지)
DEFAULT_DPI=400

# 2. 전처리 활성화
ENABLE_PREPROCESSING=true

# 3. 앙상블 모드 사용
# 웹 UI에서 "앙상블" 옵션 선택
```

---

## 성능 최적화

### 1. 리소스 할당 최적화

#### 권장 플랜별 설정

**무료 플랜 (512MB)**
```bash
WORKER_PROCESSES=1
MAX_CONCURRENT_UPLOADS=2
DEFAULT_DPI=200  # DPI 낮춤
```

**스타터 플랜 (1GB) - 권장**
```bash
WORKER_PROCESSES=2
MAX_CONCURRENT_UPLOADS=5
DEFAULT_DPI=300
```

**프로 플랜 (2GB)**
```bash
WORKER_PROCESSES=4
MAX_CONCURRENT_UPLOADS=10
DEFAULT_DPI=400
```

### 2. 응답 시간 개선

#### 정적 파일 캐싱
프론트엔드 파일에 캐시 헤더 추가 (자동 적용됨):
```
Cache-Control: public, max-age=31536000
```

#### 이미지 전처리 최적화
```bash
# 처리가 빠른 옵션만 활성화
ENABLE_PREPROCESSING=true
# 웹 UI에서 "빠른 처리" 옵션 선택
```

### 3. 동시성 제어

```bash
# 동시 업로드 수 제한으로 메모리 안정화
MAX_CONCURRENT_UPLOADS=5

# 워커 타임아웃 설정
WORKER_TIMEOUT=300  # 5분
```

### 4. 모니터링 설정

#### Cloudtype 모니터링 활용
- CPU 사용률 확인
- 메모리 사용량 추적
- 요청 응답 시간 모니터링

#### 커스텀 헬스체크
```python
# backend/main.py에 이미 구현됨
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "K-OCR Web Corrector",
        "version": "1.0.0"
    }
```

---

## 비용 안내

### Cloudtype 요금제 (2024년 기준)

| 플랜 | CPU | Memory | Storage | 가격 |
|------|-----|--------|---------|------|
| Free | 0.25 vCPU | 512 MB | 1 GB | 무료 |
| Starter | 0.5 vCPU | 1 GB | 10 GB | ~₩10,000/월 |
| Pro | 1 vCPU | 2 GB | 20 GB | ~₩30,000/월 |

### K-OCR 권장 플랜

- **개발/테스트**: Free 플랜
- **소규모 운영**: Starter 플랜 (권장)
- **상용 서비스**: Pro 플랜 이상

---

## 보안 체크리스트

배포 전 확인사항:

- [ ] `SECRET_KEY` 환경 변수를 안전한 랜덤 값으로 설정
- [ ] `DEBUG=false` 설정
- [ ] `CORS_ORIGINS`에 실제 도메인만 포함
- [ ] `TRUSTED_HOSTS`에 배포 도메인 추가
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] API 키나 비밀번호가 코드에 하드코딩되지 않았는지 확인
- [ ] HTTPS 사용 (Cloudtype 자동 제공)
- [ ] 파일 업로드 크기 제한 적절히 설정
- [ ] 임시 파일 자동 삭제 설정 (TTL)

---

## CI/CD 자동화

### GitHub Actions 연동

`.github/workflows/deploy.yml` 생성:

```yaml
name: Deploy to Cloudtype

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Trigger Cloudtype deployment
        run: |
          # Cloudtype webhook 호출 (Cloudtype 대시보드에서 webhook URL 확인)
          curl -X POST ${{ secrets.CLOUDTYPE_WEBHOOK_URL }}
```

**설정 방법:**
1. GitHub 저장소 → Settings → Secrets
2. `CLOUDTYPE_WEBHOOK_URL` 추가
3. Cloudtype 대시보드에서 webhook URL 복사하여 입력

---

## 추가 리소스

### 공식 문서
- [Cloudtype 공식 문서](https://docs.cloudtype.io/)
- [K-OCR GitHub 저장소](https://github.com/Maccrey/Auto-OCR)
- [FastAPI 문서](https://fastapi.tiangolo.com/)

### 지원
- Cloudtype 고객 지원: support@cloudtype.io
- K-OCR 이슈: GitHub Issues

### 관련 가이드
- [CLAUDE.md](./CLAUDE.md) - 개발 가이드
- [README.md](./README.md) - 프로젝트 개요
- [tasklist.md](./tasklist.md) - 개발 진행 상황

---

## 체크리스트

배포 전 최종 확인:

### 코드 준비
- [ ] 모든 변경사항 Git 커밋 완료
- [ ] GitHub에 푸시 완료
- [ ] `Dockerfile` 존재 확인
- [ ] `requirements.txt` 존재 확인

### 환경 설정
- [ ] `.env.example` 파일 확인
- [ ] 프로덕션 환경 변수 준비 완료
- [ ] `SECRET_KEY` 안전하게 생성

### Cloudtype 설정
- [ ] Cloudtype 계정 생성
- [ ] GitHub 저장소 연동
- [ ] 리소스 플랜 선택
- [ ] 환경 변수 입력
- [ ] 포트 설정 (8000)

### 배포 후
- [ ] `/health` 엔드포인트 확인
- [ ] 메인 페이지 접속 테스트
- [ ] 파일 업로드 기능 테스트
- [ ] API 문서 접근 확인
- [ ] 로그 확인

---

## 문제 발생 시

1. **Cloudtype 로그 확인**
   - 대시보드 → 프로젝트 → 로그 탭

2. **GitHub Issues 검색**
   - 유사한 문제가 있는지 확인

3. **환경 변수 재확인**
   - 필수 변수가 모두 설정되었는지 확인

4. **로컬 테스트**
   ```bash
   # 로컬에서 Docker로 테스트
   docker build -t k-ocr-test .
   docker run -p 8000:8000 -e PORT=8000 k-ocr-test
   ```

5. **Cloudtype 지원팀 문의**
   - 이메일: support@cloudtype.io
   - 문서: https://docs.cloudtype.io/

---

## 마무리

이 가이드를 따라 K-OCR Web Corrector를 Cloudtype에 성공적으로 배포하셨기를 바랍니다!

배포 후 추가 기능이 필요하거나 문제가 발생하면 GitHub Issues에 문의해 주세요.

**Happy Deploying! 🚀**
