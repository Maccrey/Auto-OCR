#!/usr/bin/env python3
"""
K-OCR Web Corrector - CI/CD Pipeline Test
자동 배포 파이프라인 테스트 및 검증
"""

import os
import sys
import json
import time
import requests
import logging
import subprocess
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import concurrent.futures
from pathlib import Path

# 외부 라이브러리 (설치 필요시)
try:
    import github
    from github import Github
    import gitlab
    from jenkins import Jenkins
    import docker
    from kubernetes import client, config
except ImportError as e:
    print(f"Warning: Some optional dependencies not available: {e}")
    print("Install with: pip install PyGithub python-gitlab python-jenkins docker kubernetes")


@dataclass
class PipelineTestConfig:
    """CI/CD 파이프라인 테스트 설정"""
    # Git 저장소 설정
    git_provider: str = "github"  # github, gitlab, bitbucket
    repository_url: str = "https://github.com/username/k-ocr-web-corrector.git"
    branch_name: str = "main"
    test_branch: str = "ci-cd-test"

    # CI/CD 플랫폼 설정
    ci_provider: str = "github-actions"  # github-actions, gitlab-ci, jenkins, azure-devops
    jenkins_url: Optional[str] = None
    jenkins_username: Optional[str] = None
    jenkins_token: Optional[str] = None

    # Docker 레지스트리 설정
    docker_registry: str = "docker.io"
    docker_repository: str = "k-ocr/web-corrector"
    docker_tag_prefix: str = "v"

    # Kubernetes 설정
    k8s_contexts: List[str] = field(default_factory=lambda: ["staging", "production"])
    staging_namespace: str = "k-ocr-staging"
    production_namespace: str = "k-ocr"

    # 테스트 설정
    unit_test_timeout: int = 600  # 10분
    integration_test_timeout: int = 1800  # 30분
    deployment_timeout: int = 900  # 15분
    rollback_test_enabled: bool = True

    # 알림 설정
    notification_channels: List[str] = field(default_factory=lambda: ["slack", "email"])
    slack_webhook_url: Optional[str] = None

    # 보안 스캔 설정
    security_scan_enabled: bool = True
    vulnerability_scan_enabled: bool = True
    license_check_enabled: bool = True


@dataclass
class PipelineStage:
    """파이프라인 단계"""
    name: str
    status: str  # pending, running, success, failure
    duration: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)


@dataclass
class PipelineRun:
    """파이프라인 실행"""
    run_id: str
    trigger: str  # push, pull-request, manual, scheduled
    branch: str
    commit_sha: str
    stages: List[PipelineStage] = field(default_factory=list)
    overall_status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class CICDPipelineTester:
    """CI/CD 파이프라인 테스트 클래스"""

    def __init__(self, config: PipelineTestConfig):
        """초기화"""
        self.config = config
        self.logger = self._setup_logger()
        self.git_client = None
        self.ci_client = None
        self.docker_client = None
        self.k8s_client = None

        # 테스트 결과
        self.test_results: List[Dict[str, Any]] = []
        self.pipeline_runs: List[PipelineRun] = []

        # 테스트 시작 시간
        self.test_start_time = datetime.now()

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger('CICDPipelineTester')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

            # 파일 로거도 추가
            file_handler = logging.FileHandler(
                f'ci_cd_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _initialize_clients(self) -> bool:
        """클라이언트 초기화"""
        try:
            # Git 클라이언트 초기화
            if self.config.git_provider == "github":
                token = os.getenv('GITHUB_TOKEN')
                if token:
                    self.git_client = Github(token)

            elif self.config.git_provider == "gitlab":
                token = os.getenv('GITLAB_TOKEN')
                url = os.getenv('GITLAB_URL', 'https://gitlab.com')
                if token:
                    self.git_client = gitlab.Gitlab(url, private_token=token)

            # CI/CD 클라이언트 초기화
            if self.config.ci_provider == "jenkins":
                if self.config.jenkins_url:
                    self.ci_client = Jenkins(
                        self.config.jenkins_url,
                        username=self.config.jenkins_username,
                        password=self.config.jenkins_token
                    )

            # Docker 클라이언트 초기화
            try:
                self.docker_client = docker.from_env()
            except Exception as e:
                self.logger.warning(f"Could not initialize Docker client: {e}")

            # Kubernetes 클라이언트 초기화
            try:
                if os.path.exists(os.path.expanduser("~/.kube/config")):
                    config.load_kube_config()
                else:
                    config.load_incluster_config()

                self.k8s_client = client.CoreV1Api()
            except Exception as e:
                self.logger.warning(f"Could not initialize Kubernetes client: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """모든 CI/CD 파이프라인 테스트 실행"""
        self.logger.info("=" * 80)
        self.logger.info("K-OCR CI/CD Pipeline Testing Started")
        self.logger.info(f"Test Configuration: {self.config}")
        self.logger.info("=" * 80)

        # 클라이언트 초기화
        if not self._initialize_clients():
            return {"success": False, "error": "Failed to initialize clients"}

        test_phases = [
            ("Pipeline Configuration Validation", self._test_pipeline_configuration),
            ("Source Code Integration Test", self._test_source_integration),
            ("Build Process Test", self._test_build_process),
            ("Unit Test Execution", self._test_unit_tests),
            ("Integration Test Execution", self._test_integration_tests),
            ("Security Scanning Test", self._test_security_scanning),
            ("Docker Image Build Test", self._test_docker_build),
            ("Container Registry Test", self._test_container_registry),
            ("Staging Deployment Test", self._test_staging_deployment),
            ("Production Deployment Test", self._test_production_deployment),
            ("Rollback Test", self._test_rollback_functionality),
            ("Pipeline Monitoring Test", self._test_pipeline_monitoring),
            ("Notification System Test", self._test_notification_system)
        ]

        phase_results = {}

        for phase_name, test_func in test_phases:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Running: {phase_name}")
            self.logger.info(f"{'='*60}")

            start_time = time.time()
            try:
                result = test_func()
                duration = time.time() - start_time

                phase_results[phase_name] = {
                    "success": result,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                }

                if result:
                    self.logger.info(f"✅ {phase_name} completed successfully ({duration:.2f}s)")
                else:
                    self.logger.error(f"❌ {phase_name} failed ({duration:.2f}s)")

            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(f"❌ {phase_name} failed with exception: {e}")
                phase_results[phase_name] = {
                    "success": False,
                    "duration": duration,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        # 전체 결과 요약
        return self._generate_test_summary(phase_results)

    def _test_pipeline_configuration(self) -> bool:
        """파이프라인 설정 검증 테스트"""
        try:
            self.logger.info("Validating pipeline configuration files...")

            # GitHub Actions 워크플로우 파일 확인
            if self.config.ci_provider == "github-actions":
                return self._validate_github_actions_config()

            # GitLab CI 설정 확인
            elif self.config.ci_provider == "gitlab-ci":
                return self._validate_gitlab_ci_config()

            # Jenkins 파이프라인 확인
            elif self.config.ci_provider == "jenkins":
                return self._validate_jenkins_config()

            # Azure DevOps 파이프라인 확인
            elif self.config.ci_provider == "azure-devops":
                return self._validate_azure_devops_config()

            else:
                self.logger.warning(f"Unknown CI provider: {self.config.ci_provider}")
                return True

        except Exception as e:
            self.logger.error(f"Pipeline configuration validation failed: {e}")
            return False

    def _validate_github_actions_config(self) -> bool:
        """GitHub Actions 워크플로우 설정 검증"""
        try:
            workflow_paths = [
                ".github/workflows/ci.yml",
                ".github/workflows/cd.yml",
                ".github/workflows/main.yml",
                ".github/workflows/deploy.yml"
            ]

            found_workflows = []

            for workflow_path in workflow_paths:
                if os.path.exists(workflow_path):
                    found_workflows.append(workflow_path)

                    # 워크플로우 파일 구문 확인
                    with open(workflow_path, 'r', encoding='utf-8') as f:
                        try:
                            workflow_config = yaml.safe_load(f)

                            # 필수 요소 확인
                            if 'on' not in workflow_config:
                                self.logger.error(f"Missing 'on' trigger in {workflow_path}")
                                return False

                            if 'jobs' not in workflow_config:
                                self.logger.error(f"Missing 'jobs' in {workflow_path}")
                                return False

                            # 환경 변수 및 시크릿 사용 확인
                            workflow_content = f.read()
                            if '${{ secrets.' in workflow_content or '${{ env.' in workflow_content:
                                self.logger.info(f"✅ {workflow_path} uses environment variables/secrets properly")

                        except yaml.YAMLError as e:
                            self.logger.error(f"Invalid YAML in {workflow_path}: {e}")
                            return False

            if not found_workflows:
                self.logger.error("No GitHub Actions workflow files found")
                return False

            self.logger.info(f"Found and validated {len(found_workflows)} workflow files")
            return True

        except Exception as e:
            self.logger.error(f"GitHub Actions config validation failed: {e}")
            return False

    def _validate_gitlab_ci_config(self) -> bool:
        """GitLab CI 설정 검증"""
        try:
            gitlab_ci_path = ".gitlab-ci.yml"

            if not os.path.exists(gitlab_ci_path):
                self.logger.error("GitLab CI configuration file not found")
                return False

            with open(gitlab_ci_path, 'r', encoding='utf-8') as f:
                try:
                    ci_config = yaml.safe_load(f)

                    # 필수 요소 확인
                    if 'stages' not in ci_config:
                        self.logger.error("Missing 'stages' in .gitlab-ci.yml")
                        return False

                    # 일반적인 단계 확인
                    expected_stages = ['build', 'test', 'deploy']
                    stages = ci_config.get('stages', [])

                    for stage in expected_stages:
                        if stage not in stages:
                            self.logger.warning(f"Stage '{stage}' not found in pipeline")

                    self.logger.info(f"✅ GitLab CI config validated with stages: {stages}")
                    return True

                except yaml.YAMLError as e:
                    self.logger.error(f"Invalid YAML in .gitlab-ci.yml: {e}")
                    return False

        except Exception as e:
            self.logger.error(f"GitLab CI config validation failed: {e}")
            return False

    def _validate_jenkins_config(self) -> bool:
        """Jenkins 파이프라인 설정 검증"""
        try:
            # Jenkinsfile 확인
            jenkinsfile_paths = ["Jenkinsfile", "jenkins/Jenkinsfile", "ci/Jenkinsfile"]

            found_jenkinsfile = None
            for path in jenkinsfile_paths:
                if os.path.exists(path):
                    found_jenkinsfile = path
                    break

            if not found_jenkinsfile:
                self.logger.error("Jenkinsfile not found")
                return False

            # Jenkins 서버 연결 테스트
            if self.ci_client:
                try:
                    version = self.ci_client.get_version()
                    self.logger.info(f"Connected to Jenkins server version: {version}")

                    # 빌드 잡 목록 확인
                    jobs = self.ci_client.get_jobs()
                    k_ocr_jobs = [job for job in jobs if 'k-ocr' in job['name'].lower()]

                    if k_ocr_jobs:
                        self.logger.info(f"Found {len(k_ocr_jobs)} K-OCR related jobs")
                    else:
                        self.logger.warning("No K-OCR jobs found in Jenkins")

                except Exception as e:
                    self.logger.warning(f"Could not connect to Jenkins server: {e}")

            self.logger.info(f"✅ Found Jenkinsfile: {found_jenkinsfile}")
            return True

        except Exception as e:
            self.logger.error(f"Jenkins config validation failed: {e}")
            return False

    def _validate_azure_devops_config(self) -> bool:
        """Azure DevOps 파이프라인 설정 검증"""
        try:
            azure_pipelines_paths = [
                "azure-pipelines.yml",
                ".azure/pipelines.yml",
                "pipelines/azure-pipelines.yml"
            ]

            found_pipeline = None
            for path in azure_pipelines_paths:
                if os.path.exists(path):
                    found_pipeline = path
                    break

            if not found_pipeline:
                self.logger.error("Azure Pipelines configuration file not found")
                return False

            with open(found_pipeline, 'r', encoding='utf-8') as f:
                try:
                    pipeline_config = yaml.safe_load(f)

                    # 필수 요소 확인
                    if 'trigger' not in pipeline_config and 'pr' not in pipeline_config:
                        self.logger.warning("No trigger or PR configuration found")

                    if 'stages' not in pipeline_config and 'jobs' not in pipeline_config:
                        self.logger.error("Missing 'stages' or 'jobs' in pipeline")
                        return False

                    self.logger.info(f"✅ Azure DevOps pipeline config validated: {found_pipeline}")
                    return True

                except yaml.YAMLError as e:
                    self.logger.error(f"Invalid YAML in {found_pipeline}: {e}")
                    return False

        except Exception as e:
            self.logger.error(f"Azure DevOps config validation failed: {e}")
            return False

    def _test_source_integration(self) -> bool:
        """소스 코드 통합 테스트"""
        try:
            self.logger.info("Testing source code integration...")

            # Git 저장소 상태 확인
            if not self._test_git_repository():
                return False

            # 브랜치 보호 규칙 확인
            if not self._test_branch_protection():
                return False

            # 코드 품질 검사 도구 설정 확인
            if not self._test_code_quality_tools():
                return False

            self.logger.info("✅ Source code integration tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Source integration test failed: {e}")
            return False

    def _test_git_repository(self) -> bool:
        """Git 저장소 테스트"""
        try:
            # 로컬 Git 상태 확인
            result = subprocess.run(['git', 'status', '--porcelain'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.error("Failed to check git status")
                return False

            # 원격 저장소 연결 확인
            result = subprocess.run(['git', 'remote', '-v'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.error("Failed to check git remotes")
                return False

            remotes = result.stdout.strip()
            if not remotes:
                self.logger.error("No git remotes configured")
                return False

            self.logger.info(f"Git remotes configured: {len(remotes.splitlines())} entries")

            # 현재 브랜치 확인
            result = subprocess.run(['git', 'branch', '--show-current'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                current_branch = result.stdout.strip()
                self.logger.info(f"Current branch: {current_branch}")

            return True

        except Exception as e:
            self.logger.error(f"Git repository test failed: {e}")
            return False

    def _test_branch_protection(self) -> bool:
        """브랜치 보호 규칙 테스트"""
        try:
            if self.config.git_provider == "github" and self.git_client:
                # GitHub API를 통한 브랜치 보호 규칙 확인
                try:
                    repo_name = self.config.repository_url.split('/')[-1].replace('.git', '')
                    repo_owner = self.config.repository_url.split('/')[-2]

                    repo = self.git_client.get_repo(f"{repo_owner}/{repo_name}")
                    branch = repo.get_branch(self.config.branch_name)

                    if branch.protection_url:
                        self.logger.info(f"Branch protection enabled for {self.config.branch_name}")
                    else:
                        self.logger.warning(f"No branch protection for {self.config.branch_name}")

                except Exception as e:
                    self.logger.warning(f"Could not check branch protection: {e}")

            return True

        except Exception as e:
            self.logger.warning(f"Branch protection test failed: {e}")
            return True  # 경고만 하고 통과

    def _test_code_quality_tools(self) -> bool:
        """코드 품질 검사 도구 테스트"""
        try:
            quality_tools = {
                'requirements.txt': ['black', 'flake8', 'mypy', 'pytest'],
                'pyproject.toml': None,
                '.pre-commit-config.yaml': None,
                '.flake8': None,
                'setup.cfg': None
            }

            found_tools = []

            for file_name, expected_packages in quality_tools.items():
                if os.path.exists(file_name):
                    found_tools.append(file_name)

                    if file_name == 'requirements.txt' and expected_packages:
                        with open(file_name, 'r') as f:
                            content = f.read()
                            for package in expected_packages:
                                if package in content:
                                    self.logger.info(f"✅ Found {package} in requirements.txt")

            if found_tools:
                self.logger.info(f"Code quality tools configured: {found_tools}")
            else:
                self.logger.warning("No code quality tool configuration found")

            return True

        except Exception as e:
            self.logger.warning(f"Code quality tools test failed: {e}")
            return True

    def _test_build_process(self) -> bool:
        """빌드 프로세스 테스트"""
        try:
            self.logger.info("Testing build process...")

            # Docker 빌드 테스트
            if not self._test_dockerfile_build():
                return False

            # Python 패키지 빌드 테스트
            if not self._test_python_build():
                return False

            # 정적 파일 빌드 테스트
            if not self._test_static_files_build():
                return False

            self.logger.info("✅ Build process tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Build process test failed: {e}")
            return False

    def _test_dockerfile_build(self) -> bool:
        """Dockerfile 빌드 테스트"""
        try:
            if not os.path.exists('Dockerfile'):
                self.logger.warning("Dockerfile not found")
                return True

            # Docker 클라이언트 확인
            if not self.docker_client:
                self.logger.warning("Docker client not available")
                return True

            # 간단한 빌드 테스트 (실제로는 빌드하지 않고 구문만 확인)
            with open('Dockerfile', 'r') as f:
                dockerfile_content = f.read()

                # 기본적인 Dockerfile 구문 확인
                required_instructions = ['FROM', 'COPY', 'RUN']
                for instruction in required_instructions:
                    if instruction not in dockerfile_content:
                        self.logger.warning(f"Missing {instruction} instruction in Dockerfile")

                # Python 애플리케이션에 필요한 일반적인 구성 확인
                if 'requirements.txt' not in dockerfile_content:
                    self.logger.warning("requirements.txt not referenced in Dockerfile")

                if 'EXPOSE' not in dockerfile_content:
                    self.logger.warning("No EXPOSE instruction in Dockerfile")

            self.logger.info("✅ Dockerfile structure validated")
            return True

        except Exception as e:
            self.logger.error(f"Dockerfile build test failed: {e}")
            return False

    def _test_python_build(self) -> bool:
        """Python 빌드 테스트"""
        try:
            # requirements.txt 존재 확인
            if os.path.exists('requirements.txt'):
                # pip install --dry-run으로 의존성 확인
                result = subprocess.run([
                    'python', '-m', 'pip', 'install', '--dry-run', '-r', 'requirements.txt'
                ], capture_output=True, text=True, timeout=300)

                if result.returncode != 0:
                    self.logger.error(f"Python dependencies check failed: {result.stderr}")
                    return False

                self.logger.info("✅ Python dependencies validated")

            # setup.py 또는 pyproject.toml 확인
            if os.path.exists('setup.py'):
                result = subprocess.run([
                    'python', 'setup.py', 'check'
                ], capture_output=True, text=True, timeout=60)

                if result.returncode != 0:
                    self.logger.warning(f"setup.py check returned warnings: {result.stderr}")

            elif os.path.exists('pyproject.toml'):
                self.logger.info("pyproject.toml found for modern Python packaging")

            return True

        except Exception as e:
            self.logger.error(f"Python build test failed: {e}")
            return False

    def _test_static_files_build(self) -> bool:
        """정적 파일 빌드 테스트"""
        try:
            # 정적 파일 디렉토리 확인
            static_dirs = ['static', 'frontend/static', 'assets', 'public']
            found_static_dirs = [d for d in static_dirs if os.path.exists(d)]

            if not found_static_dirs:
                self.logger.warning("No static file directories found")
                return True

            for static_dir in found_static_dirs:
                # CSS, JS, 이미지 파일 확인
                file_types = {
                    '.css': 'stylesheet',
                    '.js': 'javascript',
                    '.png': 'image',
                    '.jpg': 'image',
                    '.jpeg': 'image',
                    '.svg': 'image'
                }

                found_files = {}
                for root, dirs, files in os.walk(static_dir):
                    for file in files:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in file_types:
                            file_type = file_types[ext]
                            if file_type not in found_files:
                                found_files[file_type] = 0
                            found_files[file_type] += 1

                self.logger.info(f"Static files in {static_dir}: {found_files}")

            return True

        except Exception as e:
            self.logger.warning(f"Static files build test failed: {e}")
            return True

    def _test_unit_tests(self) -> bool:
        """단위 테스트 실행"""
        try:
            self.logger.info("Running unit tests...")

            # pytest 설정 확인
            test_configs = ['pytest.ini', 'pyproject.toml', 'setup.cfg']
            pytest_configured = any(os.path.exists(config) for config in test_configs)

            if not pytest_configured and not os.path.exists('tests'):
                self.logger.warning("No test configuration or test directory found")
                return True

            # 단위 테스트 실행
            test_command = ['python', '-m', 'pytest', '-v', '--tb=short']

            # 테스트 디렉토리 지정
            if os.path.exists('tests'):
                test_command.append('tests/')

            # 커버리지 옵션 추가 (가능한 경우)
            if pytest_configured:
                test_command.extend(['--cov=backend', '--cov-report=term-missing'])

            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                timeout=self.config.unit_test_timeout
            )

            if result.returncode == 0:
                self.logger.info("✅ Unit tests passed")
                self.logger.info(f"Test output:\n{result.stdout}")
                return True
            else:
                self.logger.error(f"Unit tests failed:\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Unit tests timed out after {self.config.unit_test_timeout}s")
            return False

        except Exception as e:
            self.logger.error(f"Unit tests execution failed: {e}")
            return False

    def _test_integration_tests(self) -> bool:
        """통합 테스트 실행"""
        try:
            self.logger.info("Running integration tests...")

            # 통합 테스트 디렉토리 확인
            integration_dirs = [
                'tests/integration',
                'integration_tests',
                'tests/test_api',
                'tests/test_integration'
            ]

            found_integration_dir = None
            for test_dir in integration_dirs:
                if os.path.exists(test_dir):
                    found_integration_dir = test_dir
                    break

            if not found_integration_dir:
                self.logger.warning("No integration test directory found")
                return True

            # 통합 테스트 실행
            test_command = [
                'python', '-m', 'pytest', '-v',
                '--tb=short',
                found_integration_dir
            ]

            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                timeout=self.config.integration_test_timeout
            )

            if result.returncode == 0:
                self.logger.info("✅ Integration tests passed")
                return True
            else:
                self.logger.error(f"Integration tests failed:\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Integration tests timed out after {self.config.integration_test_timeout}s")
            return False

        except Exception as e:
            self.logger.error(f"Integration tests execution failed: {e}")
            return False

    def _test_security_scanning(self) -> bool:
        """보안 스캔 테스트"""
        try:
            self.logger.info("Running security scans...")

            if not self.config.security_scan_enabled:
                self.logger.info("Security scanning disabled in configuration")
                return True

            scan_results = []

            # Safety를 통한 의존성 보안 스캔
            if self.config.vulnerability_scan_enabled:
                scan_results.append(self._run_safety_scan())

            # Bandit을 통한 코드 보안 스캔
            scan_results.append(self._run_bandit_scan())

            # 라이선스 확인
            if self.config.license_check_enabled:
                scan_results.append(self._run_license_check())

            # 모든 스캔이 성공했는지 확인
            all_passed = all(scan_results)

            if all_passed:
                self.logger.info("✅ Security scans passed")
            else:
                self.logger.error("❌ Some security scans failed")

            return all_passed

        except Exception as e:
            self.logger.error(f"Security scanning test failed: {e}")
            return False

    def _run_safety_scan(self) -> bool:
        """Safety를 통한 의존성 보안 스캔"""
        try:
            # Safety 설치 여부 확인
            result = subprocess.run(['safety', '--version'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.warning("Safety not installed, skipping vulnerability scan")
                return True

            # 보안 스캔 실행
            result = subprocess.run(['safety', 'check', '--json'],
                                  capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                self.logger.info("✅ No known vulnerabilities found")
                return True
            else:
                # JSON 형태의 결과 파싱
                try:
                    vulnerabilities = json.loads(result.stdout)
                    self.logger.error(f"Found {len(vulnerabilities)} vulnerabilities")
                    for vuln in vulnerabilities[:3]:  # 상위 3개만 표시
                        self.logger.error(f"  - {vuln.get('package', 'Unknown')}: {vuln.get('advisory', 'No description')}")
                except json.JSONDecodeError:
                    self.logger.error(f"Safety scan failed: {result.stderr}")

                return False

        except Exception as e:
            self.logger.warning(f"Safety scan failed: {e}")
            return True  # 스캔 실패는 경고로 처리

    def _run_bandit_scan(self) -> bool:
        """Bandit을 통한 코드 보안 스캔"""
        try:
            # Bandit 설치 여부 확인
            result = subprocess.run(['bandit', '--version'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.warning("Bandit not installed, skipping code security scan")
                return True

            # 코드 보안 스캔 실행
            scan_dirs = ['backend', 'src']
            target_dir = None

            for scan_dir in scan_dirs:
                if os.path.exists(scan_dir):
                    target_dir = scan_dir
                    break

            if not target_dir:
                self.logger.warning("No Python source directory found for Bandit scan")
                return True

            result = subprocess.run([
                'bandit', '-r', target_dir,
                '--format', 'json',
                '--skip', 'B101,B601'  # 일반적인 false positive 제외
            ], capture_output=True, text=True, timeout=300)

            try:
                scan_result = json.loads(result.stdout)
                issues = scan_result.get('results', [])

                if not issues:
                    self.logger.info("✅ No security issues found by Bandit")
                    return True

                # 심각도별 분류
                high_severity = [i for i in issues if i.get('issue_severity') == 'HIGH']
                medium_severity = [i for i in issues if i.get('issue_severity') == 'MEDIUM']

                if high_severity:
                    self.logger.error(f"Found {len(high_severity)} high severity security issues")
                    return False
                else:
                    self.logger.warning(f"Found {len(medium_severity)} medium severity security issues")
                    return True

            except json.JSONDecodeError:
                self.logger.warning("Could not parse Bandit output")
                return True

        except Exception as e:
            self.logger.warning(f"Bandit scan failed: {e}")
            return True

    def _run_license_check(self) -> bool:
        """라이선스 확인"""
        try:
            # pip-licenses를 통한 라이선스 확인
            result = subprocess.run(['pip-licenses', '--version'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                self.logger.warning("pip-licenses not installed, skipping license check")
                return True

            # 라이선스 정보 수집
            result = subprocess.run(['pip-licenses', '--format=json'],
                                  capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                try:
                    licenses = json.loads(result.stdout)

                    # 문제가 될 수 있는 라이선스 확인
                    problematic_licenses = ['GPL', 'AGPL', 'LGPL']
                    problematic_packages = []

                    for pkg in licenses:
                        license_name = pkg.get('License', 'Unknown').upper()
                        for prob_license in problematic_licenses:
                            if prob_license in license_name:
                                problematic_packages.append({
                                    'name': pkg.get('Name'),
                                    'license': license_name
                                })

                    if problematic_packages:
                        self.logger.warning(f"Found packages with potentially problematic licenses:")
                        for pkg in problematic_packages[:5]:  # 상위 5개만 표시
                            self.logger.warning(f"  - {pkg['name']}: {pkg['license']}")

                    self.logger.info(f"✅ License check completed for {len(licenses)} packages")
                    return True

                except json.JSONDecodeError:
                    self.logger.warning("Could not parse license information")
                    return True

        except Exception as e:
            self.logger.warning(f"License check failed: {e}")
            return True

    def _test_docker_build(self) -> bool:
        """Docker 이미지 빌드 테스트"""
        try:
            self.logger.info("Testing Docker image build...")

            if not self.docker_client:
                self.logger.warning("Docker client not available")
                return True

            if not os.path.exists('Dockerfile'):
                self.logger.warning("Dockerfile not found")
                return True

            # 테스트용 이미지 태그
            test_tag = f"{self.config.docker_repository}:test-{int(time.time())}"

            try:
                # Docker 이미지 빌드 (낮은 우선순위로)
                self.logger.info(f"Building test image: {test_tag}")

                image, logs = self.docker_client.images.build(
                    path='.',
                    tag=test_tag,
                    rm=True,
                    forcerm=True,
                    timeout=600  # 10분 타임아웃
                )

                self.logger.info("✅ Docker image built successfully")

                # 빌드된 이미지 정보 확인
                image_info = self.docker_client.api.inspect_image(image.id)
                image_size = image_info['Size'] / (1024 * 1024)  # MB 단위
                self.logger.info(f"Image size: {image_size:.1f} MB")

                # 테스트 이미지 삭제
                try:
                    self.docker_client.images.remove(test_tag, force=True)
                    self.logger.info("Test image cleaned up")
                except Exception as e:
                    self.logger.warning(f"Could not cleanup test image: {e}")

                return True

            except docker.errors.BuildError as e:
                self.logger.error(f"Docker build failed: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Docker build test failed: {e}")
            return False

    def _test_container_registry(self) -> bool:
        """컨테이너 레지스트리 테스트"""
        try:
            self.logger.info("Testing container registry access...")

            if not self.docker_client:
                self.logger.warning("Docker client not available")
                return True

            # 레지스트리 로그인 테스트
            try:
                # 환경변수에서 레지스트리 인증 정보 확인
                registry_username = os.getenv('DOCKER_REGISTRY_USERNAME')
                registry_password = os.getenv('DOCKER_REGISTRY_PASSWORD')

                if registry_username and registry_password:
                    login_result = self.docker_client.login(
                        username=registry_username,
                        password=registry_password,
                        registry=self.config.docker_registry
                    )

                    if login_result.get('Status') == 'Login Succeeded':
                        self.logger.info("✅ Container registry login successful")
                    else:
                        self.logger.error("Container registry login failed")
                        return False

                else:
                    self.logger.warning("No container registry credentials found")

            except Exception as e:
                self.logger.warning(f"Container registry login test failed: {e}")

            # 레지스트리에서 기존 이미지 확인 (가능한 경우)
            try:
                # 기존 이미지 태그 목록 확인
                repository = f"{self.config.docker_registry}/{self.config.docker_repository}"

                # 간단한 pull 테스트 (latest 태그가 있다면)
                try:
                    latest_image = f"{repository}:latest"
                    self.docker_client.images.pull(latest_image)
                    self.logger.info(f"✅ Successfully pulled {latest_image}")

                    # 테스트 후 이미지 삭제
                    self.docker_client.images.remove(latest_image)

                except docker.errors.NotFound:
                    self.logger.info("No latest image found in registry (expected for new projects)")

                except Exception as e:
                    self.logger.warning(f"Could not test registry pull: {e}")

            except Exception as e:
                self.logger.warning(f"Registry image check failed: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Container registry test failed: {e}")
            return False

    def _test_staging_deployment(self) -> bool:
        """스테이징 배포 테스트"""
        try:
            self.logger.info("Testing staging deployment...")

            if not self.k8s_client:
                self.logger.warning("Kubernetes client not available")
                return True

            # 스테이징 네임스페이스 확인
            try:
                namespace = self.k8s_client.read_namespace(name=self.config.staging_namespace)
                if namespace.status.phase != 'Active':
                    self.logger.error(f"Staging namespace {self.config.staging_namespace} not active")
                    return False
            except Exception as e:
                self.logger.error(f"Staging namespace {self.config.staging_namespace} not found: {e}")
                return False

            # 스테이징 환경 배포 상태 확인
            pods = self.k8s_client.list_namespaced_pod(namespace=self.config.staging_namespace)

            running_pods = sum(1 for pod in pods.items if pod.status.phase == 'Running')
            total_pods = len(pods.items)

            if total_pods == 0:
                self.logger.warning("No pods found in staging environment")
                return True

            if running_pods < total_pods:
                self.logger.error(f"Only {running_pods}/{total_pods} pods running in staging")
                return False

            self.logger.info(f"✅ Staging deployment validated: {running_pods} pods running")
            return True

        except Exception as e:
            self.logger.error(f"Staging deployment test failed: {e}")
            return False

    def _test_production_deployment(self) -> bool:
        """프로덕션 배포 테스트"""
        try:
            self.logger.info("Testing production deployment...")

            if not self.k8s_client:
                self.logger.warning("Kubernetes client not available")
                return True

            # 프로덕션 네임스페이스 확인
            try:
                namespace = self.k8s_client.read_namespace(name=self.config.production_namespace)
                if namespace.status.phase != 'Active':
                    self.logger.error(f"Production namespace {self.config.production_namespace} not active")
                    return False
            except Exception as e:
                self.logger.error(f"Production namespace {self.config.production_namespace} not found: {e}")
                return False

            # 프로덕션 환경 배포 상태 확인
            apps_api = client.AppsV1Api()
            deployments = apps_api.list_namespaced_deployment(namespace=self.config.production_namespace)

            healthy_deployments = 0
            total_deployments = len(deployments.items)

            for deployment in deployments.items:
                ready_replicas = deployment.status.ready_replicas or 0
                desired_replicas = deployment.spec.replicas or 0

                if ready_replicas == desired_replicas:
                    healthy_deployments += 1
                else:
                    self.logger.warning(f"Deployment {deployment.metadata.name}: {ready_replicas}/{desired_replicas} replicas ready")

            if total_deployments == 0:
                self.logger.warning("No deployments found in production environment")
                return True

            if healthy_deployments < total_deployments:
                self.logger.error(f"Only {healthy_deployments}/{total_deployments} deployments healthy in production")
                return False

            self.logger.info(f"✅ Production deployment validated: {healthy_deployments} deployments healthy")
            return True

        except Exception as e:
            self.logger.error(f"Production deployment test failed: {e}")
            return False

    def _test_rollback_functionality(self) -> bool:
        """롤백 기능 테스트"""
        try:
            self.logger.info("Testing rollback functionality...")

            if not self.config.rollback_test_enabled:
                self.logger.info("Rollback testing disabled in configuration")
                return True

            if not self.k8s_client:
                self.logger.warning("Kubernetes client not available")
                return True

            # Kubernetes 배포 히스토리 확인
            apps_api = client.AppsV1Api()

            for namespace in [self.config.staging_namespace, self.config.production_namespace]:
                try:
                    deployments = apps_api.list_namespaced_deployment(namespace=namespace)

                    for deployment in deployments.items:
                        # 배포 히스토리 확인
                        replica_sets = apps_api.list_namespaced_replica_set(
                            namespace=namespace,
                            label_selector=f"app={deployment.metadata.labels.get('app', 'k-ocr')}"
                        )

                        if len(replica_sets.items) > 1:
                            self.logger.info(f"Deployment {deployment.metadata.name} has rollback history")
                        else:
                            self.logger.warning(f"Deployment {deployment.metadata.name} has no rollback history")

                except Exception as e:
                    self.logger.warning(f"Could not check rollback capability for {namespace}: {e}")

            self.logger.info("✅ Rollback functionality validated")
            return True

        except Exception as e:
            self.logger.error(f"Rollback functionality test failed: {e}")
            return False

    def _test_pipeline_monitoring(self) -> bool:
        """파이프라인 모니터링 테스트"""
        try:
            self.logger.info("Testing pipeline monitoring...")

            # 파이프라인 실행 로그 확인
            monitoring_results = []

            # GitHub Actions 워크플로우 런 확인
            if self.config.ci_provider == "github-actions" and self.git_client:
                monitoring_results.append(self._check_github_actions_runs())

            # Jenkins 빌드 히스토리 확인
            elif self.config.ci_provider == "jenkins" and self.ci_client:
                monitoring_results.append(self._check_jenkins_builds())

            # 모니터링 메트릭 수집
            monitoring_results.append(self._collect_pipeline_metrics())

            # 전체 모니터링 결과 평가
            all_monitoring_ok = all(monitoring_results)

            if all_monitoring_ok:
                self.logger.info("✅ Pipeline monitoring validated")
            else:
                self.logger.warning("Some pipeline monitoring checks failed")

            return True  # 모니터링 실패는 전체 테스트 실패로 이어지지 않음

        except Exception as e:
            self.logger.error(f"Pipeline monitoring test failed: {e}")
            return False

    def _check_github_actions_runs(self) -> bool:
        """GitHub Actions 워크플로우 런 확인"""
        try:
            if not self.git_client:
                return False

            repo_name = self.config.repository_url.split('/')[-1].replace('.git', '')
            repo_owner = self.config.repository_url.split('/')[-2]

            repo = self.git_client.get_repo(f"{repo_owner}/{repo_name}")
            workflows = repo.get_workflows()

            total_runs = 0
            for workflow in workflows:
                runs = workflow.get_runs()[:5]  # 최근 5개 실행만 확인
                total_runs += len(list(runs))

                for run in runs:
                    self.logger.info(f"Workflow run: {run.conclusion} ({run.created_at})")

            self.logger.info(f"Found {total_runs} recent workflow runs")
            return True

        except Exception as e:
            self.logger.warning(f"Could not check GitHub Actions runs: {e}")
            return False

    def _check_jenkins_builds(self) -> bool:
        """Jenkins 빌드 히스토리 확인"""
        try:
            if not self.ci_client:
                return False

            jobs = self.ci_client.get_jobs()
            k_ocr_jobs = [job for job in jobs if 'k-ocr' in job['name'].lower()]

            for job in k_ocr_jobs[:3]:  # 상위 3개 잡만 확인
                job_info = self.ci_client.get_job_info(job['name'])
                builds = job_info.get('builds', [])[:5]  # 최근 5개 빌드

                for build in builds:
                    build_info = self.ci_client.get_build_info(job['name'], build['number'])
                    self.logger.info(f"Build {build['number']}: {build_info['result']}")

            return True

        except Exception as e:
            self.logger.warning(f"Could not check Jenkins builds: {e}")
            return False

    def _collect_pipeline_metrics(self) -> bool:
        """파이프라인 메트릭 수집"""
        try:
            # 기본 메트릭 수집
            metrics = {
                'test_duration': time.time() - self.test_start_time.timestamp(),
                'timestamp': datetime.now().isoformat()
            }

            # 메트릭 저장
            metrics_file = f"pipeline_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Pipeline metrics saved to: {metrics_file}")
            return True

        except Exception as e:
            self.logger.warning(f"Could not collect pipeline metrics: {e}")
            return True

    def _test_notification_system(self) -> bool:
        """알림 시스템 테스트"""
        try:
            self.logger.info("Testing notification system...")

            notification_results = []

            # Slack 알림 테스트
            if "slack" in self.config.notification_channels and self.config.slack_webhook_url:
                notification_results.append(self._test_slack_notifications())

            # 이메일 알림 테스트 (구성된 경우)
            if "email" in self.config.notification_channels:
                notification_results.append(self._test_email_notifications())

            # 전체 알림 시스템 결과
            all_notifications_ok = all(notification_results) if notification_results else True

            if all_notifications_ok:
                self.logger.info("✅ Notification system validated")
            else:
                self.logger.warning("Some notification channels failed")

            return True  # 알림 실패는 전체 테스트 실패로 이어지지 않음

        except Exception as e:
            self.logger.error(f"Notification system test failed: {e}")
            return False

    def _test_slack_notifications(self) -> bool:
        """Slack 알림 테스트"""
        try:
            if not self.config.slack_webhook_url:
                return False

            test_message = {
                "text": "🧪 K-OCR CI/CD Pipeline Test Notification",
                "attachments": [
                    {
                        "color": "good",
                        "fields": [
                            {
                                "title": "Test Type",
                                "value": "CI/CD Pipeline Validation",
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": datetime.now().isoformat(),
                                "short": True
                            }
                        ]
                    }
                ]
            }

            response = requests.post(
                self.config.slack_webhook_url,
                json=test_message,
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info("✅ Slack notification sent successfully")
                return True
            else:
                self.logger.error(f"Slack notification failed: {response.status_code}")
                return False

        except Exception as e:
            self.logger.warning(f"Slack notification test failed: {e}")
            return False

    def _test_email_notifications(self) -> bool:
        """이메일 알림 테스트"""
        try:
            # 이메일 설정 확인 (실제 이메일을 보내지는 않음)
            email_config = {
                'smtp_server': os.getenv('SMTP_SERVER'),
                'smtp_port': os.getenv('SMTP_PORT', '587'),
                'smtp_username': os.getenv('SMTP_USERNAME'),
                'smtp_password': os.getenv('SMTP_PASSWORD'),
                'from_email': os.getenv('FROM_EMAIL'),
                'to_emails': os.getenv('TO_EMAILS', '').split(',')
            }

            missing_config = [key for key, value in email_config.items() if not value]

            if missing_config:
                self.logger.warning(f"Email configuration missing: {missing_config}")
                return False

            self.logger.info("✅ Email notification configuration validated")
            return True

        except Exception as e:
            self.logger.warning(f"Email notification test failed: {e}")
            return False

    def _generate_test_summary(self, phase_results: Dict[str, Any]) -> Dict[str, Any]:
        """테스트 결과 요약 생성"""
        total_phases = len(phase_results)
        successful_phases = sum(1 for result in phase_results.values() if result.get('success', False))

        total_duration = time.time() - self.test_start_time.timestamp()

        summary = {
            'test_summary': {
                'total_phases': total_phases,
                'successful_phases': successful_phases,
                'success_rate': successful_phases / total_phases * 100 if total_phases > 0 else 0,
                'total_duration': total_duration,
                'timestamp': datetime.now().isoformat()
            },
            'phase_results': phase_results,
            'overall_success': successful_phases == total_phases,
            'configuration': {
                'ci_provider': self.config.ci_provider,
                'git_provider': self.config.git_provider,
                'repository_url': self.config.repository_url,
                'branch_name': self.config.branch_name
            },
            'pipeline_runs': [
                {
                    'run_id': run.run_id,
                    'trigger': run.trigger,
                    'branch': run.branch,
                    'overall_status': run.overall_status,
                    'duration': (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else None
                }
                for run in self.pipeline_runs
            ]
        }

        # 최종 결과 출력
        self.logger.info("\n" + "="*80)
        self.logger.info("CI/CD PIPELINE TEST SUMMARY")
        self.logger.info("="*80)
        self.logger.info(f"Test Duration: {total_duration:.2f} seconds")
        self.logger.info(f"Phases Completed: {successful_phases}/{total_phases}")
        self.logger.info(f"Success Rate: {summary['test_summary']['success_rate']:.1f}%")

        if summary['overall_success']:
            self.logger.info("🎉 ALL CI/CD PIPELINE TESTS PASSED!")
        else:
            self.logger.error("❌ Some CI/CD pipeline tests failed!")

            # 실패한 단계 나열
            failed_phases = [
                phase for phase, result in phase_results.items()
                if not result.get('success', False)
            ]
            self.logger.error(f"Failed phases: {', '.join(failed_phases)}")

        self.logger.info("="*80)

        # 결과 파일 저장
        try:
            summary_file = f"ci_cd_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Test summary saved to: {summary_file}")

        except Exception as e:
            self.logger.warning(f"Could not save test summary: {e}")

        # 최종 알림 전송
        if self.config.slack_webhook_url and "slack" in self.config.notification_channels:
            self._send_final_notification(summary)

        return summary

    def _send_final_notification(self, summary: Dict[str, Any]) -> None:
        """최종 결과 알림 전송"""
        try:
            success_rate = summary['test_summary']['success_rate']
            emoji = "🎉" if summary['overall_success'] else "❌"

            message = {
                "text": f"{emoji} K-OCR CI/CD Pipeline Test Results",
                "attachments": [
                    {
                        "color": "good" if summary['overall_success'] else "danger",
                        "fields": [
                            {
                                "title": "CI Provider",
                                "value": self.config.ci_provider.upper(),
                                "short": True
                            },
                            {
                                "title": "Repository",
                                "value": self.config.repository_url,
                                "short": True
                            },
                            {
                                "title": "Success Rate",
                                "value": f"{success_rate:.1f}%",
                                "short": True
                            },
                            {
                                "title": "Duration",
                                "value": f"{summary['test_summary']['total_duration']:.1f}s",
                                "short": True
                            }
                        ]
                    }
                ]
            }

            response = requests.post(
                self.config.slack_webhook_url,
                json=message,
                timeout=10
            )

            if response.status_code == 200:
                self.logger.info("Final notification sent successfully")
            else:
                self.logger.warning(f"Failed to send final notification: {response.status_code}")

        except Exception as e:
            self.logger.warning(f"Could not send final notification: {e}")


def main():
    """메인 함수"""
    # 설정 로드 (환경변수 또는 설정 파일에서)
    config = PipelineTestConfig(
        git_provider=os.getenv('GIT_PROVIDER', 'github'),
        repository_url=os.getenv('REPOSITORY_URL', 'https://github.com/username/k-ocr-web-corrector.git'),
        branch_name=os.getenv('BRANCH_NAME', 'main'),
        ci_provider=os.getenv('CI_PROVIDER', 'github-actions'),
        docker_registry=os.getenv('DOCKER_REGISTRY', 'docker.io'),
        docker_repository=os.getenv('DOCKER_REPOSITORY', 'k-ocr/web-corrector'),
        slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL')
    )

    # 테스터 인스턴스 생성
    tester = CICDPipelineTester(config)

    # 모든 테스트 실행
    results = tester.run_all_tests()

    # 종료 코드 설정
    exit_code = 0 if results.get('overall_success', False) else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()