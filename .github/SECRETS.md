# GitHub Secrets 설정 가이드

CI/CD 파이프라인이 정상적으로 작동하려면 다음 GitHub Secrets을 설정해야 합니다.

## Repository Secrets

GitHub 저장소의 Settings > Secrets and variables > Actions에서 다음 시크릿들을 설정하세요:

### Docker Hub (선택사항)
Docker Hub에 이미지를 푸시하려는 경우:
- `DOCKER_USERNAME`: Docker Hub 사용자명
- `DOCKER_PASSWORD`: Docker Hub 액세스 토큰

### 배포 관련
- `STAGING_HOST`: 스테이징 서버 호스트
- `PRODUCTION_HOST`: 프로덕션 서버 호스트
- `DEPLOY_SSH_KEY`: 배포 서버 SSH 개인키
- `DEPLOY_USER`: 배포 서버 사용자명

### 알림 관련 (선택사항)
- `SLACK_WEBHOOK_URL`: Slack 웹훅 URL
- `DISCORD_WEBHOOK_URL`: Discord 웹훅 URL

## Environment Secrets

각 환경별로 다음 시크릿들을 설정하세요:

### Staging Environment
Settings > Environments > staging에서 설정:
- `STAGING_DATABASE_URL`: 스테이징 데이터베이스 URL
- `STAGING_REDIS_URL`: 스테이징 Redis URL
- `STAGING_SECRET_KEY`: 애플리케이션 시크릿 키

### Production Environment  
Settings > Environments > production에서 설정:
- `PRODUCTION_DATABASE_URL`: 프로덕션 데이터베이스 URL
- `PRODUCTION_REDIS_URL`: 프로덕션 Redis URL
- `PRODUCTION_SECRET_KEY`: 애플리케이션 시크릿 키

## 자동 생성되는 시크릿

다음 시크릿들은 GitHub에서 자동으로 제공됩니다:
- `GITHUB_TOKEN`: GitHub API 액세스용 (자동 생성)

## 보안 고려사항

1. **최소 권한 원칙**: 각 시크릿은 필요한 최소한의 권한만 부여
2. **주기적 갱신**: 시크릿 키들을 주기적으로 교체
3. **환경 분리**: 스테이징과 프로덕션 환경의 시크릿을 분리
4. **접근 제한**: Environment secrets을 사용하여 배포 승인 프로세스 구현

## 설정 확인

시크릿 설정 후 다음 단계로 확인:
1. 테스트 커밋을 푸시하여 CI/CD 파이프라인 동작 확인
2. Actions 탭에서 워크플로우 실행 로그 확인
3. 각 환경별 배포 테스트 실행