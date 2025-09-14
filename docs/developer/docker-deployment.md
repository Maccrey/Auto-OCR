# K-OCR Web Corrector - Docker 배포 가이드

## 🐳 Docker 배포 개요

이 가이드는 K-OCR Web Corrector를 Docker를 사용하여 배포하는 방법을 설명합니다. 개발 환경부터 프로덕션 환경까지 다양한 시나리오를 다룹니다.

## 📋 사전 요구사항

### 필수 소프트웨어
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Git**: 최신 버전

### 권장 하드웨어
```bash
개발 환경:
- RAM: 4GB+
- CPU: 2코어+
- 디스크: 10GB+ 여유공간

프로덕션 환경:
- RAM: 8GB+
- CPU: 4코어+
- 디스크: 50GB+ 여유공간
```

### 시스템 확인
```bash
# Docker 버전 확인
docker --version
# Docker version 24.0.0+

# Docker Compose 버전 확인
docker-compose --version
# Docker Compose version 2.20.0+

# 시스템 리소스 확인
docker system info | grep -E "(Total Memory|CPUs)"
```

## 🚀 빠른 시작

### 1단계: 저장소 클론
```bash
git clone <repository-url>
cd AutoOCR
```

### 2단계: 환경변수 설정
```bash
# 환경변수 파일 복사
cp .env.example .env

# 개발용 설정 (기본값 사용 가능)
# 프로덕션용은 보안 설정 필수 변경
```

### 3단계: Docker Compose 실행
```bash
# 개발 환경 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build

# 특정 서비스만 실행
docker-compose up redis web worker
```

### 4단계: 서비스 확인
```bash
# 웹 애플리케이션: http://localhost:8000
# API 문서: http://localhost:8000/api/docs
# Flower 모니터링: http://localhost:5555 (활성화된 경우)

# 헬스체크 확인
curl http://localhost:8000/health
```

## 📊 Docker 아키텍처

### 컨테이너 구조
```
┌─────────────────────────────────────────────┐
│              Docker Host                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Nginx     │  │     K-OCR Web       │   │
│  │  (Proxy)    │  │     (FastAPI)       │   │
│  │   :80/443   │  │      :8000          │   │
│  └─────────────┘  └─────────────────────┘   │
│         │                     │             │
│         └─────────────────────┘             │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Redis     │  │   Celery Workers    │   │
│  │  (Queue)    │  │  (Background Jobs)  │   │
│  │   :6379     │  │    Multiple         │   │
│  └─────────────┘  └─────────────────────┘   │
│         │                     │             │
│         └─────────────────────┘             │
│                                             │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ PostgreSQL  │  │    Monitoring       │   │
│  │ (Metadata)  │  │  (Prometheus/       │   │
│  │   :5432     │  │   Grafana/Flower)   │   │
│  └─────────────┘  └─────────────────────┘   │
│                                             │
└─────────────────────────────────────────────┘

Network: k-ocr-network (bridge)
Volumes: redis_data, postgres_data, temp_storage
```

### 서비스별 컨테이너 세부사항

#### Web 서비스 (FastAPI)
```dockerfile
# Dockerfile 구조
FROM python:3.11-slim as base
├── System packages (Tesseract, OpenCV)
├── Python dependencies
├── Application code
└── Entry point (Uvicorn)

Resources:
- Memory: 1GB limit, 256MB reserved
- CPU: 1 core limit, 0.25 core reserved
- Ports: 8000 (internal)
- Health check: /health endpoint
```

#### Worker 서비스 (Celery)
```dockerfile
# Same base image as web service
FROM k-ocr-web:latest

Command: celery -A backend.core.tasks worker
Resources:
- Memory: 2GB limit, 512MB reserved
- CPU: 2 cores limit, 0.5 core reserved
- Scales: 2-5 instances based on load
```

#### Redis (Message Broker)
```yaml
Configuration:
- Image: redis:7-alpine
- Memory: 512MB limit
- Persistence: AOF enabled
- Eviction: allkeys-lru
- Health check: redis-cli ping
```

## 🔧 상세 설정 가이드

### 환경별 Docker Compose 파일

#### 개발 환경 (docker-compose.dev.yml)
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    volumes:
      # 코드 변경 시 자동 리로드
      - ./backend:/app/backend:delegated
      - ./frontend:/app/frontend:delegated
      - ./tests:/app/tests:delegated
    environment:
      - DEBUG=true
      - ENVIRONMENT=development
      - LOG_LEVEL=DEBUG
    command: >
      uvicorn backend.main:app
      --host 0.0.0.0
      --port 8000
      --reload
    ports:
      - "8000:8000"

  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: development
    volumes:
      - ./backend:/app/backend:delegated
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: >
      celery -A backend.core.tasks worker
      --loglevel=debug
      --concurrency=2

  # 개발용 도구
  adminer:
    image: adminer:latest
    ports:
      - "8080:8080"
    depends_on:
      - postgres

  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "1025:1025"  # SMTP
      - "8025:8025"  # Web UI

# 사용법: docker-compose -f docker-compose.dev.yml up
```

#### 스테이징 환경 (docker-compose.staging.yml)
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      - ENVIRONMENT=staging
      - DEBUG=false
      - LOG_LEVEL=INFO
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      - ENVIRONMENT=staging
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure

  # 모니터링 추가
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
```

#### 프로덕션 환경 (docker-compose.prod.yml)
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - web
    deploy:
      restart_policy:
        condition: always

  web:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=WARNING
    deploy:
      replicas: 4
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 5
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 256M
          cpus: '0.25'

  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    deploy:
      replicas: 8
      restart_policy:
        condition: on-failure
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 512M
          cpus: '0.5'

# 사용법: docker-compose -f docker-compose.prod.yml up -d
```

### 환경변수 설정 파일

#### .env.development
```bash
# 개발 환경 설정
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# 서버 설정
HOST=0.0.0.0
PORT=8000

# Redis 설정 (개발용)
REDIS_URL=redis://redis:6379/0
REDIS_PORT=6379

# PostgreSQL 설정 (개발용)
POSTGRES_DB=k_ocr_dev
POSTGRES_USER=dev_user
POSTGRES_PASSWORD=dev_password
POSTGRES_PORT=5432

# 파일 저장 설정
TEMP_STORAGE_PATH=/app/temp_storage
MAX_FILE_SIZE=52428800
FILE_RETENTION_HOURS=24

# OCR 설정
DEFAULT_OCR_ENGINE=paddleocr
DEFAULT_DPI=300
CONFIDENCE_THRESHOLD=0.7

# 보안 설정 (개발용)
SECRET_KEY=development-secret-key-change-in-production
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080", "*"]

# Celery 설정
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKERS=2
CELERY_CONCURRENCY=2

# 모니터링 설정
ENABLE_METRICS=true
METRICS_PORT=9090
FLOWER_PORT=5555
```

#### .env.production
```bash
# 프로덕션 환경 설정
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# 서버 설정
HOST=0.0.0.0
PORT=8000

# Redis 설정 (프로덕션용)
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your-secure-redis-password
REDIS_MAX_CONNECTIONS=20

# PostgreSQL 설정 (프로덕션용)
POSTGRES_DB=k_ocr_prod
POSTGRES_USER=k_ocr_prod_user
POSTGRES_PASSWORD=your-very-secure-database-password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# 파일 저장 설정
TEMP_STORAGE_PATH=/app/temp_storage
MAX_FILE_SIZE=52428800
FILE_RETENTION_HOURS=24
CLEANUP_INTERVAL_MINUTES=60

# OCR 설정
DEFAULT_OCR_ENGINE=paddleocr
DEFAULT_DPI=300
CONFIDENCE_THRESHOLD=0.7
ENABLE_GPU=false

# 보안 설정 (프로덕션용 - 반드시 변경!)
SECRET_KEY=your-very-secure-secret-key-here
CORS_ORIGINS=["https://your-domain.com"]
ALLOWED_HOSTS=["your-domain.com", "www.your-domain.com"]

# Celery 설정
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKERS=8
CELERY_CONCURRENCY=4
CELERY_MAX_TASKS_PER_CHILD=100

# SSL/TLS 설정
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem

# 모니터링 설정
ENABLE_METRICS=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
FLOWER_PORT=5555

# 알림 설정
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

## 🛠️ Docker 빌드 최적화

### 멀티스테이지 빌드 최적화
```dockerfile
# Dockerfile 최적화 예시
FROM python:3.11-slim as base
# 기본 시스템 패키지 설치

FROM base as dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
# OCR 모델 다운로드
RUN python -c "import paddleocr; paddleocr.PaddleOCR(lang='korean')"

FROM base as development
COPY --from=dependencies /root/.local /root/.local
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--reload"]

FROM base as production
COPY --from=dependencies /root/.local /root/.local
COPY . .
RUN python -m compileall backend/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--workers", "4"]

# 빌드 명령어
# docker build --target development -t k-ocr:dev .
# docker build --target production -t k-ocr:prod .
```

### .dockerignore 최적화
```gitignore
# .dockerignore
**/__pycache__
**/*.pyc
**/*.pyo
**/*.pyd
**/.Python
**/env
**/pip-log.txt
**/pip-delete-this-directory.txt
**/.tox
**/.coverage
**/.coverage.*
**/.cache
**/nosetests.xml
**/coverage.xml
**/*.cover
**/*.log
**/.git
**/.mypy_cache
**/.pytest_cache
**/.hypothesis

# 개발 파일들
.env.development
.env.staging
.env.local
docker-compose.dev.yml
docker-compose.override.yml

# 문서 및 설정 파일
docs/
README.md
.github/
.vscode/
.idea/

# 테스트 파일
tests/
**/*test*.py

# 대용량 파일들
temp_storage/
logs/
*.log
*.pdf
*.png
*.jpg
*.jpeg
```

## 🚀 배포 자동화

### GitHub Actions CI/CD
```yaml
# .github/workflows/docker-deploy.yml
name: Docker Build and Deploy

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Container Registry
      if: github.event_name != 'pull_request'
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        target: production
        push: ${{ github.event_name != 'pull_request' }}
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Run security scan
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
        format: 'sarif'
        output: 'trivy-results.sarif'

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to production
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/k-ocr
          docker-compose -f docker-compose.prod.yml pull
          docker-compose -f docker-compose.prod.yml up -d --remove-orphans
          docker system prune -f
```

### 배포 스크립트
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-production}
echo "🚀 K-OCR 배포 시작 (환경: $ENVIRONMENT)"

# 환경별 설정 파일 선택
case $ENVIRONMENT in
  development)
    COMPOSE_FILE="docker-compose.dev.yml"
    ;;
  staging)
    COMPOSE_FILE="docker-compose.staging.yml"
    ;;
  production)
    COMPOSE_FILE="docker-compose.prod.yml"
    ;;
  *)
    echo "❌ 잘못된 환경: $ENVIRONMENT"
    echo "사용 가능한 환경: development, staging, production"
    exit 1
    ;;
esac

echo "📁 환경 파일 확인: $COMPOSE_FILE"

# 환경변수 파일 확인
ENV_FILE=".env.$ENVIRONMENT"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 환경변수 파일을 찾을 수 없습니다: $ENV_FILE"
    exit 1
fi

# Docker 및 Docker Compose 버전 확인
echo "🔍 Docker 환경 확인"
docker --version
docker-compose --version

# 이미지 빌드
echo "🏗️ Docker 이미지 빌드"
docker-compose -f $COMPOSE_FILE build --no-cache

# 서비스 중지 (graceful shutdown)
echo "⏹️ 기존 서비스 중지"
docker-compose -f $COMPOSE_FILE down --remove-orphans

# 데이터베이스 마이그레이션 (필요한 경우)
if [ "$ENVIRONMENT" = "production" ]; then
    echo "📊 데이터베이스 마이그레이션"
    docker-compose -f $COMPOSE_FILE run --rm web python -m alembic upgrade head
fi

# 서비스 시작
echo "🚀 서비스 시작"
docker-compose -f $COMPOSE_FILE up -d

# 헬스체크 대기
echo "🔍 서비스 상태 확인"
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 서비스가 정상적으로 시작되었습니다"
        break
    fi

    if [ $i -eq 30 ]; then
        echo "❌ 서비스 시작 실패 - 헬스체크 타임아웃"
        docker-compose -f $COMPOSE_FILE logs web
        exit 1
    fi

    echo "⏳ 서비스 시작 대기... ($i/30)"
    sleep 2
done

# 정리
echo "🧹 사용하지 않는 Docker 리소스 정리"
docker system prune -f --volumes

echo "✅ 배포 완료!"
echo "🌐 서비스 URL:"
echo "  - 웹 애플리케이션: http://localhost:8000"
echo "  - API 문서: http://localhost:8000/api/docs"

if [ "$ENVIRONMENT" = "development" ]; then
    echo "  - Adminer: http://localhost:8080"
    echo "  - MailHog: http://localhost:8025"
fi

if [ "$ENVIRONMENT" != "development" ]; then
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000"
fi
```

## 📊 모니터링 및 로깅

### Docker 로그 설정
```yaml
# docker-compose.yml 로깅 설정
version: '3.8'

services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
        labels: "service=web,environment=production"

  worker:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "3"
        labels: "service=worker,environment=production"

# 중앙집중식 로깅 (ELK Stack)
  elasticsearch:
    image: elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: logstash:8.8.0
    volumes:
      - ./config/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    depends_on:
      - elasticsearch

  kibana:
    image: kibana:8.8.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
```

### 컨테이너 모니터링
```bash
# 컨테이너 상태 모니터링 스크립트
#!/bin/bash
# scripts/monitor.sh

echo "🔍 K-OCR Docker 컨테이너 모니터링"
echo "=================================="

# 실행 중인 컨테이너 상태
echo "📊 컨테이너 상태:"
docker-compose ps

echo ""
echo "💾 리소스 사용량:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

echo ""
echo "🏥 헬스체크 상태:"
for container in k-ocr-web k-ocr-worker k-ocr-redis; do
    status=$(docker inspect --format='{{.State.Health.Status}}' $container 2>/dev/null || echo "not-found")
    echo "  $container: $status"
done

echo ""
echo "📝 최근 로그 (마지막 10줄):"
echo "--- Web Server ---"
docker-compose logs --tail=10 web

echo ""
echo "--- Worker ---"
docker-compose logs --tail=10 worker

echo ""
echo "💽 볼륨 사용량:"
docker system df

echo ""
echo "📈 Redis 통계:"
docker-compose exec redis redis-cli info memory | grep -E "(used_memory_human|maxmemory_human)"
```

## 🛡️ 보안 강화

### Docker 보안 설정
```yaml
# security-hardened docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    user: "1000:1000"  # non-root user
    read_only: true
    tmpfs:
      - /tmp
      - /run
    volumes:
      - ./temp_storage:/app/temp_storage:rw
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    sysctls:
      - net.ipv4.ip_unprivileged_port_start=0

  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --protected-mode yes
    volumes:
      - redis_data:/data:rw
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL

networks:
  k-ocr-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Nginx 보안 설정
```nginx
# config/nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 보안 헤더
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # 성능 최적화
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 압축
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # 업로드 크기 제한
    client_max_body_size 50m;
    client_body_timeout 60s;
    client_header_timeout 60s;

    upstream fastapi {
        server web:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name your-domain.com www.your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com www.your-domain.com;

        # SSL 설정
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:MozTLS:10m;
        ssl_session_tickets off;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # API 및 정적 파일
        location / {
            proxy_pass http://fastapi;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket 지원
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # 타임아웃 설정
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 정적 파일 최적화
        location /static/ {
            alias /app/frontend/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # 헬스체크
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

## 🎛️ 운영 도구 및 스크립트

### 관리 스크립트 모음
```bash
#!/bin/bash
# scripts/manage.sh - 종합 관리 스크립트

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

show_help() {
    echo "K-OCR Docker 관리 도구"
    echo ""
    echo "사용법: ./scripts/manage.sh [명령어] [옵션]"
    echo ""
    echo "명령어:"
    echo "  start [env]     - 서비스 시작 (기본: development)"
    echo "  stop            - 서비스 중지"
    echo "  restart [env]   - 서비스 재시작"
    echo "  status          - 서비스 상태 확인"
    echo "  logs [service]  - 로그 확인"
    echo "  shell [service] - 컨테이너 쉘 접속"
    echo "  update          - 이미지 업데이트 및 재시작"
    echo "  backup          - 데이터 백업"
    echo "  restore [file]  - 데이터 복구"
    echo "  cleanup         - 정리 작업"
    echo "  monitor         - 실시간 모니터링"
    echo ""
    echo "예시:"
    echo "  ./scripts/manage.sh start production"
    echo "  ./scripts/manage.sh logs web"
    echo "  ./scripts/manage.sh shell worker"
}

get_compose_file() {
    local env=${1:-development}
    case $env in
        development) echo "docker-compose.dev.yml" ;;
        staging) echo "docker-compose.staging.yml" ;;
        production) echo "docker-compose.prod.yml" ;;
        *) echo "docker-compose.yml" ;;
    esac
}

start_services() {
    local env=${1:-development}
    local compose_file=$(get_compose_file $env)

    echo "🚀 K-OCR 서비스 시작 (환경: $env)"
    docker-compose -f $compose_file up -d --build

    echo "⏳ 서비스 준비 대기..."
    sleep 10

    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 서비스가 정상적으로 시작되었습니다"
    else
        echo "❌ 서비스 시작에 문제가 있습니다. 로그를 확인해주세요."
        docker-compose -f $compose_file logs web
    fi
}

stop_services() {
    echo "⏹️ K-OCR 서비스 중지"
    for compose_file in docker-compose.*.yml docker-compose.yml; do
        if [ -f "$compose_file" ]; then
            docker-compose -f $compose_file down --remove-orphans
        fi
    done
}

show_status() {
    echo "📊 K-OCR 서비스 상태"
    echo "==================="

    # 컨테이너 상태
    docker-compose ps

    echo ""
    echo "💾 리소스 사용량:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

    echo ""
    echo "🌐 서비스 엔드포인트:"
    echo "  - 웹 애플리케이션: http://localhost:8000"
    echo "  - API 문서: http://localhost:8000/api/docs"
    echo "  - 헬스체크: http://localhost:8000/health"
}

show_logs() {
    local service=${1:-}
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f $service
    fi
}

enter_shell() {
    local service=${1:-web}
    echo "🐚 $service 컨테이너 쉘 접속"
    docker-compose exec $service /bin/bash
}

update_services() {
    echo "🔄 서비스 업데이트"
    docker-compose pull
    docker-compose up -d --remove-orphans
    docker system prune -f
}

backup_data() {
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    echo "💾 데이터 백업 시작: $backup_dir"

    # Redis 데이터 백업
    docker-compose exec redis redis-cli --rdb > "$backup_dir/redis_dump.rdb"

    # PostgreSQL 백업 (활성화된 경우)
    if docker-compose ps postgres | grep -q "Up"; then
        docker-compose exec postgres pg_dump -U k_ocr_user k_ocr > "$backup_dir/postgres_backup.sql"
    fi

    # 임시 저장소 백업
    if [ -d "temp_storage" ]; then
        tar -czf "$backup_dir/temp_storage.tar.gz" temp_storage/
    fi

    echo "✅ 백업 완료: $backup_dir"
}

restore_data() {
    local backup_file=$1
    if [ -z "$backup_file" ]; then
        echo "❌ 백업 파일을 지정해주세요"
        echo "사용법: ./scripts/manage.sh restore [backup_directory]"
        return 1
    fi

    echo "🔄 데이터 복구: $backup_file"
    # 복구 로직 구현
    echo "✅ 복구 완료"
}

cleanup() {
    echo "🧹 정리 작업 시작"

    # 중지된 컨테이너 제거
    docker container prune -f

    # 사용하지 않는 이미지 제거
    docker image prune -f

    # 사용하지 않는 볼륨 제거
    docker volume prune -f

    # 사용하지 않는 네트워크 제거
    docker network prune -f

    echo "✅ 정리 완료"
}

monitor() {
    echo "📊 실시간 모니터링 시작 (Ctrl+C로 종료)"
    watch -n 5 'echo "=== $(date) ==="; docker stats --no-stream; echo ""; docker-compose ps'
}

# 메인 로직
case "${1:-}" in
    start)
        start_services $2
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services $2
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs $2
        ;;
    shell)
        enter_shell $2
        ;;
    update)
        update_services
        ;;
    backup)
        backup_data
        ;;
    restore)
        restore_data $2
        ;;
    cleanup)
        cleanup
        ;;
    monitor)
        monitor
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ 알 수 없는 명령어: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac
```

## 🆘 트러블슈팅

### 일반적인 Docker 문제들

#### 1. 컨테이너 빌드 실패
```bash
# 문제: Docker 이미지 빌드 실패
# 해결방법:

# 캐시 무시하고 다시 빌드
docker-compose build --no-cache

# 빌드 로그 확인
docker-compose build --progress=plain

# 디스크 공간 확인
df -h
docker system df
```

#### 2. 서비스 시작 실패
```bash
# 문제: 컨테이너가 시작되지 않음
# 해결방법:

# 로그 확인
docker-compose logs service-name

# 컨테이너 상태 확인
docker-compose ps

# 포트 충돌 확인
netstat -tlnp | grep :8000
lsof -i :8000
```

#### 3. 성능 문제
```bash
# 문제: 느린 처리 속도
# 해결방법:

# 리소스 사용량 확인
docker stats

# 메모리 증설 또는 Worker 수 조정
# .env 파일에서 CELERY_WORKERS 값 변경

# 로그 레벨 조정
LOG_LEVEL=ERROR  # DEBUG 대신 ERROR 사용
```

#### 4. 네트워크 연결 문제
```bash
# 문제: 컨테이너 간 통신 실패
# 해결방법:

# 네트워크 상태 확인
docker network ls
docker network inspect k-ocr-network

# DNS 확인
docker-compose exec web nslookup redis

# 포트 바인딩 확인
docker-compose ps
```

### 데이터 복구 및 백업

#### 자동 백업 스크립트
```bash
#!/bin/bash
# scripts/auto-backup.sh

BACKUP_DIR="/opt/k-ocr-backups"
RETENTION_DAYS=7

mkdir -p $BACKUP_DIR

# 백업 파일명 (타임스탬프 포함)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/k-ocr-backup-$TIMESTAMP.tar.gz"

echo "🔄 자동 백업 시작: $BACKUP_FILE"

# 서비스 일시 중지 (선택사항)
# docker-compose pause

# 데이터 디렉토리 백업
tar -czf $BACKUP_FILE \
    temp_storage/ \
    config/ \
    .env.production \
    docker-compose.prod.yml

# Redis 백업 추가
docker-compose exec -T redis redis-cli --rdb >> $BACKUP_FILE

# 서비스 재개 (중지한 경우)
# docker-compose unpause

# 오래된 백업 파일 삭제
find $BACKUP_DIR -name "k-ocr-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ 자동 백업 완료"

# Crontab에 추가:
# 0 2 * * * /opt/k-ocr/scripts/auto-backup.sh >> /var/log/k-ocr-backup.log 2>&1
```

---

**마지막 업데이트**: 2024년 1월
**Docker 버전**: 24.0+
**Docker Compose 버전**: 2.20+