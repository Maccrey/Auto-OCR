# K-OCR 배포 테스트 스위트

K-OCR Web Corrector의 종합적인 배포 테스트 및 검증을 위한 자동화된 테스트 스위트입니다.

## 📋 개요

이 테스트 스위트는 K-OCR 애플리케이션의 배포 과정에서 발생할 수 있는 모든 단계를 자동으로 검증하여, 안정적이고 신뢰할 수 있는 배포를 보장합니다.

## 🧪 테스트 구성

### 1. 로컬 Docker 환경 테스트 (`local-docker-test.py`)
- **목적**: 개발 환경에서의 Docker 컨테이너화 검증
- **테스트 범위**:
  - Docker Compose 설정 검증
  - 컨테이너 빌드 및 실행 테스트
  - 서비스 간 연결성 검증
  - 기능 테스트 (파일 업로드, OCR 처리)
  - 성능 및 리소스 모니터링

```bash
# 실행 방법
python deploy/tests/local-docker-test.py

# 환경변수 설정 (선택적)
export DOCKER_COMPOSE_FILE=docker-compose.dev.yml
export TEST_DURATION=300
export LOAD_TEST_USERS=10
```

### 2. 스테이징 환경 배포 테스트 (`staging-deployment-test.py`)
- **목적**: 스테이징 환경에서의 배포 검증
- **지원 플랫폼**: AWS EKS/ECS, GCP GKE, Azure AKS
- **테스트 범위**:
  - 클라우드 인프라 검증
  - Kubernetes 배포 상태 확인
  - End-to-End 기능 테스트
  - 부하 테스트 및 성능 검증
  - 보안 설정 검증

```bash
# 실행 방법
python deploy/tests/staging-deployment-test.py

# 환경변수 설정
export CLOUD_PROVIDER=aws  # aws, gcp, azure
export CLUSTER_NAME=k-ocr-staging-cluster
export NAMESPACE=k-ocr-staging
export APP_DOMAIN=staging.k-ocr.yourdomain.com
```

### 3. 프로덕션 환경 배포 테스트 (`production-deployment-test.py`)
- **목적**: 프로덕션 환경에서의 배포 안정성 검증
- **테스트 범위**:
  - 프로덕션 인프라 검증
  - 애플리케이션 배포 상태 확인
  - 고가용성 및 스케일링 테스트
  - 모니터링 시스템 검증
  - 재해 복구 준비 상태 확인
  - 백업 시스템 검증

```bash
# 실행 방법
python deploy/tests/production-deployment-test.py

# 환경변수 설정
export CLOUD_PROVIDER=aws
export CLUSTER_NAME=k-ocr-production-cluster
export NAMESPACE=k-ocr
export APP_DOMAIN=k-ocr.yourdomain.com
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### 4. CI/CD 파이프라인 테스트 (`ci-cd-pipeline-test.py`)
- **목적**: 자동 배포 파이프라인의 전체 워크플로우 검증
- **지원 플랫폼**: GitHub Actions, GitLab CI, Jenkins, Azure DevOps
- **테스트 범위**:
  - 파이프라인 설정 검증
  - 빌드 프로세스 테스트
  - 단위/통합 테스트 실행
  - 보안 스캔 및 취약점 검사
  - 컨테이너 이미지 빌드
  - 자동 배포 및 롤백 기능

```bash
# 실행 방법
python deploy/tests/ci-cd-pipeline-test.py

# 환경변수 설정
export GIT_PROVIDER=github  # github, gitlab
export CI_PROVIDER=github-actions  # github-actions, gitlab-ci, jenkins
export REPOSITORY_URL=https://github.com/username/k-ocr-web-corrector.git
export GITHUB_TOKEN=ghp_xxxxx
export DOCKER_REGISTRY_USERNAME=username
export DOCKER_REGISTRY_PASSWORD=password
```

## 🚀 빠른 시작

### 필수 조건

1. **Python 3.8 이상**
2. **Docker 및 Docker Compose**
3. **kubectl 설정** (Kubernetes 테스트용)
4. **클라우드 CLI 도구** (AWS CLI, gcloud, Azure CLI)

### 의존성 설치

```bash
# 필수 패키지 설치
pip install requests pyyaml psutil

# 선택적 패키지 (클라우드/Git 연동용)
pip install boto3 google-cloud-container azure-identity azure-mgmt-containerservice
pip install kubernetes docker
pip install PyGithub python-gitlab python-jenkins
pip install prometheus-client
```

### 모든 테스트 실행

```bash
# 순차적 실행
python deploy/tests/local-docker-test.py
python deploy/tests/staging-deployment-test.py
python deploy/tests/production-deployment-test.py
python deploy/tests/ci-cd-pipeline-test.py

# 또는 스크립트로 실행 (작성 예정)
./deploy/tests/run-all-tests.sh
```

## ⚙️ 설정 가이드

### 환경변수 설정

각 테스트는 환경변수를 통해 설정할 수 있습니다:

```bash
# 공통 설정
export K8S_NAMESPACE=k-ocr
export APP_DOMAIN=k-ocr.yourdomain.com
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# AWS 설정
export AWS_REGION=ap-northeast-2
export AWS_CLUSTER_NAME=k-ocr-cluster

# GCP 설정
export GOOGLE_CLOUD_PROJECT=my-project-id
export GOOGLE_CLOUD_REGION=asia-northeast3

# Azure 설정
export AZURE_SUBSCRIPTION_ID=subscription-id
export AZURE_RESOURCE_GROUP=k-ocr-rg

# Docker 설정
export DOCKER_REGISTRY=docker.io
export DOCKER_REPOSITORY=k-ocr/web-corrector

# Git/CI 설정
export GITHUB_TOKEN=ghp_xxxxx
export GITLAB_TOKEN=glpat_xxxxx
export JENKINS_URL=https://jenkins.example.com
export JENKINS_USERNAME=admin
export JENKINS_TOKEN=api-token
```

### 설정 파일 사용

환경변수 대신 설정 파일을 사용할 수도 있습니다:

```yaml
# config/test-config.yaml
local_test:
  docker_compose_file: "docker-compose.dev.yml"
  test_duration: 300

staging_test:
  cloud_provider: "aws"
  cluster_name: "k-ocr-staging-cluster"
  namespace: "k-ocr-staging"

production_test:
  cloud_provider: "aws"
  cluster_name: "k-ocr-production-cluster"
  namespace: "k-ocr"
  monitoring_duration: 1800

pipeline_test:
  ci_provider: "github-actions"
  git_provider: "github"
  security_scan_enabled: true
```

## 📊 테스트 결과

### 결과 파일

각 테스트는 실행 후 다음과 같은 결과 파일을 생성합니다:

- **로그 파일**: `*_test_YYYYMMDD_HHMMSS.log`
- **결과 요약**: `*_test_summary_YYYYMMDD_HHMMSS.json`
- **성능 리포트**: `*_performance_report_YYYYMMDD_HHMMSS.json`

### 결과 형식

```json
{
  "test_summary": {
    "total_phases": 10,
    "successful_phases": 9,
    "success_rate": 90.0,
    "total_duration": 1200.5,
    "timestamp": "2024-01-15T10:30:00"
  },
  "phase_results": {
    "Infrastructure Validation": {
      "success": true,
      "duration": 45.2,
      "timestamp": "2024-01-15T10:15:00"
    }
  },
  "overall_success": false,
  "configuration": {
    "cloud_provider": "aws",
    "cluster_name": "k-ocr-production-cluster"
  }
}
```

### Slack 알림

Slack 웹훅 URL이 설정된 경우, 테스트 결과를 자동으로 알림으로 전송합니다:

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

## 🔧 커스터마이징

### 새로운 테스트 추가

테스트 클래스를 상속받아 새로운 테스트를 추가할 수 있습니다:

```python
from local_docker_test import LocalDockerTester

class CustomDockerTester(LocalDockerTester):
    def _test_custom_functionality(self) -> bool:
        """커스텀 기능 테스트"""
        # 테스트 로직 구현
        return True

    def run_all_tests(self) -> Dict[str, Any]:
        # 기본 테스트에 커스텀 테스트 추가
        results = super().run_all_tests()
        # 추가 테스트 실행
        return results
```

### 테스트 설정 수정

각 테스트의 `Config` 클래스를 수정하여 테스트 동작을 조정할 수 있습니다:

```python
# 로컬 테스트 설정 수정 예시
config = LocalTestConfig(
    docker_compose_file="docker-compose.custom.yml",
    test_duration=600,  # 10분으로 연장
    load_test_users=50,  # 부하 테스트 사용자 증가
    health_check_timeout=120  # 헬스체크 타임아웃 증가
)
```

## 🐛 문제 해결

### 자주 발생하는 문제

1. **Docker 연결 실패**
   ```bash
   # Docker 데몬 상태 확인
   docker ps

   # Docker Compose 파일 검증
   docker-compose config
   ```

2. **Kubernetes 클러스터 접근 실패**
   ```bash
   # kubectl 설정 확인
   kubectl config current-context
   kubectl cluster-info

   # 네임스페이스 확인
   kubectl get namespaces
   ```

3. **클라우드 인증 실패**
   ```bash
   # AWS
   aws sts get-caller-identity

   # GCP
   gcloud auth list

   # Azure
   az account show
   ```

### 로그 분석

각 테스트는 상세한 로그를 생성하므로, 문제 발생 시 로그 파일을 확인하세요:

```bash
# 최신 로그 파일 확인
ls -la *_test_*.log | tail -1

# 실시간 로그 모니터링
tail -f local_docker_test_$(date +%Y%m%d)*.log
```

## 📈 성능 최적화

### 병렬 실행

여러 테스트를 병렬로 실행하여 시간을 단축할 수 있습니다:

```bash
# GNU parallel 사용 (설치 필요)
parallel ::: \
  "python deploy/tests/local-docker-test.py" \
  "python deploy/tests/staging-deployment-test.py"

# 백그라운드 실행
python deploy/tests/local-docker-test.py &
python deploy/tests/ci-cd-pipeline-test.py &
wait
```

### 선택적 테스트 실행

환경변수를 통해 특정 테스트만 실행하도록 설정:

```bash
export SKIP_LOAD_TESTS=true
export SKIP_SECURITY_SCANS=true
export QUICK_MODE=true
```

## 🤝 기여하기

새로운 테스트나 개선사항이 있다면 다음 가이드라인을 따라 기여해주세요:

1. **테스트 작성**: 새로운 테스트는 기존 패턴을 따라 작성
2. **문서화**: README 업데이트 및 코드 주석 추가
3. **오류 처리**: 예외 상황에 대한 적절한 처리
4. **로깅**: 상세하고 유용한 로그 메시지 작성

## 📝 라이선스

이 테스트 스위트는 K-OCR Web Corrector 프로젝트의 일부로 같은 라이선스를 따릅니다.

---

**K-OCR 개발팀**
문의사항이나 버그 리포트는 이슈 트래커를 통해 제출해주세요.