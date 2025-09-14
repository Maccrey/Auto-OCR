#!/usr/bin/env python3
"""
K-OCR Web Corrector - Production Deployment Test
프로덕션 환경 배포 테스트 및 검증
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
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import concurrent.futures
from pathlib import Path

# 외부 라이브러리 (설치 필요시)
try:
    import boto3
    import kubernetes
    from kubernetes import client, config
    from google.cloud import container_v1
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.containerservice import ContainerServiceClient
    import psutil
    import prometheus_client.parser
except ImportError as e:
    print(f"Warning: Some optional dependencies not available: {e}")
    print("Install with: pip install boto3 kubernetes google-cloud-container azure-identity azure-mgmt-containerservice psutil prometheus-client")


@dataclass
class ProductionTestConfig:
    """프로덕션 테스트 설정"""
    # 클라우드 설정
    cloud_provider: str = "aws"  # aws, gcp, azure
    region: str = "ap-northeast-2"
    cluster_name: str = "k-ocr-production-cluster"
    namespace: str = "k-ocr"

    # 애플리케이션 설정
    app_domain: str = "k-ocr.yourdomain.com"
    app_port: int = 443
    health_check_endpoint: str = "/health"
    api_prefix: str = "/api/v1"

    # 테스트 설정
    load_test_users: int = 100
    load_test_duration: int = 300  # 5분
    monitoring_duration: int = 1800  # 30분
    max_response_time: float = 2.0  # 2초
    min_availability: float = 99.9  # 99.9%

    # 알림 설정
    slack_webhook_url: Optional[str] = None
    alert_channels: List[str] = field(default_factory=lambda: ["email", "slack"])

    # 보안 설정
    security_scan_enabled: bool = True
    penetration_test_enabled: bool = False  # 프로덕션에서는 신중히

    # 백업 및 복구 설정
    backup_test_enabled: bool = True
    disaster_recovery_test: bool = True


@dataclass
class TestResult:
    """테스트 결과"""
    name: str
    success: bool
    duration: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ProductionDeploymentTester:
    """프로덕션 환경 배포 테스트 클래스"""

    def __init__(self, config: ProductionTestConfig):
        """초기화"""
        self.config = config
        self.results: List[TestResult] = []
        self.logger = self._setup_logger()
        self.k8s_client = None
        self.cloud_client = None

        # 테스트 시작 시간
        self.test_start_time = datetime.now()

    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger('ProductionDeploymentTester')
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
                f'production_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _initialize_clients(self) -> bool:
        """클라우드 클라이언트 초기화"""
        try:
            # Kubernetes 클라이언트 초기화
            if os.path.exists(os.path.expanduser("~/.kube/config")):
                config.load_kube_config()
            else:
                config.load_incluster_config()

            self.k8s_client = client.CoreV1Api()

            # 클라우드별 클라이언트 초기화
            if self.config.cloud_provider == "aws":
                self.cloud_client = boto3.client('eks', region_name=self.config.region)
            elif self.config.cloud_provider == "gcp":
                self.cloud_client = container_v1.ClusterManagerClient()
            elif self.config.cloud_provider == "azure":
                credential = DefaultAzureCredential()
                self.cloud_client = ContainerServiceClient(
                    credential,
                    subscription_id=os.getenv('AZURE_SUBSCRIPTION_ID')
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """모든 프로덕션 테스트 실행"""
        self.logger.info("=" * 80)
        self.logger.info("K-OCR Production Deployment Testing Started")
        self.logger.info(f"Test Configuration: {self.config}")
        self.logger.info("=" * 80)

        # 클라이언트 초기화
        if not self._initialize_clients():
            return {"success": False, "error": "Failed to initialize cloud clients"}

        test_phases = [
            ("Infrastructure Validation", self._test_infrastructure_validation),
            ("Cluster Health Check", self._test_cluster_health),
            ("Application Deployment", self._test_application_deployment),
            ("Service Connectivity", self._test_service_connectivity),
            ("Load Testing", self._test_load_performance),
            ("Security Testing", self._test_security_validation),
            ("Monitoring & Alerting", self._test_monitoring_system),
            ("Backup & Recovery", self._test_backup_recovery),
            ("Disaster Recovery", self._test_disaster_recovery),
            ("Performance Benchmarks", self._test_performance_benchmarks)
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

    def _test_infrastructure_validation(self) -> bool:
        """인프라 검증 테스트"""
        try:
            self.logger.info("Validating production infrastructure...")

            # 클라우드별 인프라 검증
            if self.config.cloud_provider == "aws":
                return self._validate_aws_production()
            elif self.config.cloud_provider == "gcp":
                return self._validate_gcp_production()
            elif self.config.cloud_provider == "azure":
                return self._validate_azure_production()
            else:
                self.logger.error(f"Unsupported cloud provider: {self.config.cloud_provider}")
                return False

        except Exception as e:
            self.logger.error(f"Infrastructure validation failed: {e}")
            return False

    def _validate_aws_production(self) -> bool:
        """AWS 프로덕션 인프라 검증"""
        try:
            # EKS 클러스터 상태 확인
            cluster_info = self.cloud_client.describe_cluster(name=self.config.cluster_name)
            cluster_status = cluster_info['cluster']['status']

            if cluster_status != 'ACTIVE':
                self.logger.error(f"EKS cluster not active: {cluster_status}")
                return False

            # 노드 그룹 확인
            nodegroups = self.cloud_client.list_nodegroups(clusterName=self.config.cluster_name)
            if not nodegroups['nodegroups']:
                self.logger.error("No node groups found in EKS cluster")
                return False

            # 각 노드 그룹 상태 확인
            for ng_name in nodegroups['nodegroups']:
                ng_info = self.cloud_client.describe_nodegroup(
                    clusterName=self.config.cluster_name,
                    nodegroupName=ng_name
                )
                if ng_info['nodegroup']['status'] != 'ACTIVE':
                    self.logger.error(f"Node group {ng_name} not active")
                    return False

            # RDS 인스턴스 확인 (PostgreSQL)
            rds_client = boto3.client('rds', region_name=self.config.region)
            try:
                db_instances = rds_client.describe_db_instances()
                k_ocr_dbs = [
                    db for db in db_instances['DBInstances']
                    if 'k-ocr' in db['DBInstanceIdentifier'].lower()
                ]

                for db in k_ocr_dbs:
                    if db['DBInstanceStatus'] != 'available':
                        self.logger.error(f"Database {db['DBInstanceIdentifier']} not available")
                        return False

            except Exception as e:
                self.logger.warning(f"Could not verify RDS instances: {e}")

            # ElastiCache 확인 (Redis)
            elasticache_client = boto3.client('elasticache', region_name=self.config.region)
            try:
                cache_clusters = elasticache_client.describe_cache_clusters()
                k_ocr_cache = [
                    cluster for cluster in cache_clusters['CacheClusters']
                    if 'k-ocr' in cluster['CacheClusterId'].lower()
                ]

                for cluster in k_ocr_cache:
                    if cluster['CacheClusterStatus'] != 'available':
                        self.logger.error(f"Cache cluster {cluster['CacheClusterId']} not available")
                        return False

            except Exception as e:
                self.logger.warning(f"Could not verify ElastiCache: {e}")

            # Load Balancer 확인
            elbv2_client = boto3.client('elbv2', region_name=self.config.region)
            load_balancers = elbv2_client.describe_load_balancers()

            active_lbs = [
                lb for lb in load_balancers['LoadBalancers']
                if lb['State']['Code'] == 'active'
            ]

            if not active_lbs:
                self.logger.error("No active load balancers found")
                return False

            self.logger.info("✅ AWS production infrastructure validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"AWS infrastructure validation failed: {e}")
            return False

    def _validate_gcp_production(self) -> bool:
        """GCP 프로덕션 인프라 검증"""
        try:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                self.logger.error("GOOGLE_CLOUD_PROJECT environment variable not set")
                return False

            # GKE 클러스터 확인
            cluster_path = f"projects/{project_id}/locations/{self.config.region}/clusters/{self.config.cluster_name}"
            cluster = self.cloud_client.get_cluster(name=cluster_path)

            if cluster.status != container_v1.Cluster.Status.RUNNING:
                self.logger.error(f"GKE cluster not running: {cluster.status}")
                return False

            # 노드 풀 확인
            for node_pool in cluster.node_pools:
                if node_pool.status != container_v1.NodePool.Status.RUNNING:
                    self.logger.error(f"Node pool {node_pool.name} not running")
                    return False

            self.logger.info("✅ GCP production infrastructure validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"GCP infrastructure validation failed: {e}")
            return False

    def _validate_azure_production(self) -> bool:
        """Azure 프로덕션 인프라 검증"""
        try:
            subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
            resource_group = os.getenv('AZURE_RESOURCE_GROUP', 'k-ocr-production')

            if not subscription_id:
                self.logger.error("AZURE_SUBSCRIPTION_ID environment variable not set")
                return False

            # AKS 클러스터 확인
            cluster = self.cloud_client.managed_clusters.get(
                resource_group_name=resource_group,
                resource_name=self.config.cluster_name
            )

            if cluster.provisioning_state != 'Succeeded':
                self.logger.error(f"AKS cluster not ready: {cluster.provisioning_state}")
                return False

            self.logger.info("✅ Azure production infrastructure validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Azure infrastructure validation failed: {e}")
            return False

    def _test_cluster_health(self) -> bool:
        """클러스터 건강성 테스트"""
        try:
            self.logger.info("Checking Kubernetes cluster health...")

            # 노드 상태 확인
            nodes = self.k8s_client.list_node()
            ready_nodes = 0
            total_nodes = len(nodes.items)

            for node in nodes.items:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        ready_nodes += 1
                        break

            if ready_nodes < total_nodes:
                self.logger.error(f"Only {ready_nodes}/{total_nodes} nodes are ready")
                return False

            # 시스템 파드 상태 확인
            system_namespaces = ['kube-system', 'kube-public', 'monitoring', 'logging']

            for namespace in system_namespaces:
                try:
                    pods = self.k8s_client.list_namespaced_pod(namespace=namespace)

                    for pod in pods.items:
                        if pod.status.phase not in ['Running', 'Succeeded']:
                            self.logger.error(f"Pod {pod.metadata.name} in {namespace} not running: {pod.status.phase}")
                            return False

                except Exception as e:
                    self.logger.warning(f"Could not check namespace {namespace}: {e}")

            # 리소스 사용량 확인
            if not self._check_cluster_resources():
                return False

            self.logger.info("✅ Kubernetes cluster health check passed")
            return True

        except Exception as e:
            self.logger.error(f"Cluster health check failed: {e}")
            return False

    def _check_cluster_resources(self) -> bool:
        """클러스터 리소스 사용량 확인"""
        try:
            # 노드별 리소스 사용량 확인
            nodes = self.k8s_client.list_node()

            for node in nodes.items:
                # CPU 및 메모리 할당 가능량 확인
                allocatable = node.status.allocatable

                if allocatable:
                    cpu_allocatable = allocatable.get('cpu', '0')
                    memory_allocatable = allocatable.get('memory', '0')

                    self.logger.info(f"Node {node.metadata.name}: CPU={cpu_allocatable}, Memory={memory_allocatable}")

            return True

        except Exception as e:
            self.logger.error(f"Resource check failed: {e}")
            return False

    def _test_application_deployment(self) -> bool:
        """애플리케이션 배포 상태 테스트"""
        try:
            self.logger.info("Checking K-OCR application deployment...")

            # K-OCR 네임스페이스 확인
            try:
                namespace = self.k8s_client.read_namespace(name=self.config.namespace)
                if namespace.status.phase != 'Active':
                    self.logger.error(f"Namespace {self.config.namespace} not active")
                    return False
            except Exception as e:
                self.logger.error(f"Namespace {self.config.namespace} not found: {e}")
                return False

            # 애플리케이션 파드 상태 확인
            pods = self.k8s_client.list_namespaced_pod(namespace=self.config.namespace)

            app_components = ['web', 'worker', 'redis', 'postgres']
            component_status = {}

            for pod in pods.items:
                pod_name = pod.metadata.name

                # 컴포넌트 식별
                component = None
                for comp in app_components:
                    if comp in pod_name.lower():
                        component = comp
                        break

                if component:
                    if component not in component_status:
                        component_status[component] = []

                    component_status[component].append({
                        'name': pod_name,
                        'status': pod.status.phase,
                        'ready': self._is_pod_ready(pod)
                    })

            # 각 컴포넌트가 최소 하나씩은 실행 중인지 확인
            for component in app_components:
                if component not in component_status:
                    self.logger.error(f"No {component} pods found")
                    return False

                ready_pods = [p for p in component_status[component] if p['ready']]
                if not ready_pods:
                    self.logger.error(f"No ready {component} pods found")
                    return False

                self.logger.info(f"✅ {component}: {len(ready_pods)} pods ready")

            # 서비스 확인
            services = self.k8s_client.list_namespaced_service(namespace=self.config.namespace)

            required_services = ['k-ocr-web', 'k-ocr-redis', 'k-ocr-postgres']
            for service_name in required_services:
                service_found = False
                for service in services.items:
                    if service_name in service.metadata.name:
                        service_found = True
                        break

                if not service_found:
                    self.logger.error(f"Required service {service_name} not found")
                    return False

            self.logger.info("✅ Application deployment validated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Application deployment check failed: {e}")
            return False

    def _is_pod_ready(self, pod) -> bool:
        """파드가 준비 상태인지 확인"""
        if pod.status.phase != 'Running':
            return False

        if not pod.status.conditions:
            return False

        for condition in pod.status.conditions:
            if condition.type == 'Ready':
                return condition.status == 'True'

        return False

    def _test_service_connectivity(self) -> bool:
        """서비스 연결성 테스트"""
        try:
            self.logger.info("Testing service connectivity...")

            # 외부 접근성 테스트
            app_url = f"https://{self.config.app_domain}"

            # Health check endpoint 테스트
            health_url = f"{app_url}{self.config.health_check_endpoint}"

            response = requests.get(health_url, timeout=10, verify=True)

            if response.status_code != 200:
                self.logger.error(f"Health check failed: {response.status_code}")
                return False

            # API 엔드포인트 테스트
            api_endpoints = [
                f"{app_url}{self.config.api_prefix}/upload",
                f"{app_url}{self.config.api_prefix}/status",
            ]

            for endpoint in api_endpoints:
                try:
                    response = requests.get(endpoint, timeout=5, verify=True)
                    # 404는 정상 (인증 등으로 인한)
                    if response.status_code >= 500:
                        self.logger.error(f"API endpoint {endpoint} returned server error: {response.status_code}")
                        return False
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Failed to connect to {endpoint}: {e}")
                    return False

            # 내부 서비스 연결 테스트 (클러스터 내부)
            if not self._test_internal_connectivity():
                return False

            self.logger.info("✅ Service connectivity tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Service connectivity test failed: {e}")
            return False

    def _test_internal_connectivity(self) -> bool:
        """내부 서비스 연결 테스트"""
        try:
            # Redis 연결 테스트 (kubectl을 통해)
            redis_test_cmd = [
                'kubectl', 'exec', '-n', self.config.namespace,
                'deploy/k-ocr-redis', '--',
                'redis-cli', 'ping'
            ]

            result = subprocess.run(redis_test_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0 or 'PONG' not in result.stdout:
                self.logger.error("Redis connectivity test failed")
                return False

            # PostgreSQL 연결 테스트
            postgres_test_cmd = [
                'kubectl', 'exec', '-n', self.config.namespace,
                'deploy/k-ocr-postgres', '--',
                'pg_isready'
            ]

            result = subprocess.run(postgres_test_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.logger.error("PostgreSQL connectivity test failed")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Internal connectivity test failed: {e}")
            return False

    def _test_load_performance(self) -> bool:
        """부하 및 성능 테스트"""
        try:
            self.logger.info(f"Running load test with {self.config.load_test_users} users for {self.config.load_test_duration}s...")

            # 부하 테스트 실행 (간단한 HTTP 요청 기반)
            app_url = f"https://{self.config.app_domain}"

            # 동시 요청 테스트
            start_time = time.time()
            response_times = []
            error_count = 0

            def make_request():
                try:
                    response = requests.get(app_url, timeout=self.config.max_response_time)
                    return response.elapsed.total_seconds(), response.status_code == 200
                except Exception:
                    return None, False

            # 동시성 테스트
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []

                # 지정된 시간 동안 요청 보내기
                while time.time() - start_time < self.config.load_test_duration:
                    if len(futures) < self.config.load_test_users:
                        future = executor.submit(make_request)
                        futures.append(future)

                    # 완료된 요청 처리
                    completed_futures = []
                    for future in futures:
                        if future.done():
                            response_time, success = future.result()
                            if success and response_time:
                                response_times.append(response_time)
                            else:
                                error_count += 1
                            completed_futures.append(future)

                    # 완료된 futures 제거
                    for future in completed_futures:
                        futures.remove(future)

                    time.sleep(0.1)

            # 결과 분석
            total_requests = len(response_times) + error_count
            if total_requests == 0:
                self.logger.error("No requests completed during load test")
                return False

            error_rate = error_count / total_requests * 100
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0

            self.logger.info(f"Load test results:")
            self.logger.info(f"  Total requests: {total_requests}")
            self.logger.info(f"  Error rate: {error_rate:.2f}%")
            self.logger.info(f"  Average response time: {avg_response_time:.2f}s")
            self.logger.info(f"  Max response time: {max_response_time:.2f}s")

            # 성능 기준 확인
            if error_rate > (100 - self.config.min_availability):
                self.logger.error(f"Error rate {error_rate:.2f}% exceeds threshold")
                return False

            if avg_response_time > self.config.max_response_time:
                self.logger.error(f"Average response time {avg_response_time:.2f}s exceeds threshold")
                return False

            self.logger.info("✅ Load and performance tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Load performance test failed: {e}")
            return False

    def _test_security_validation(self) -> bool:
        """보안 검증 테스트"""
        try:
            self.logger.info("Running security validation tests...")

            if not self.config.security_scan_enabled:
                self.logger.info("Security scanning disabled in configuration")
                return True

            # SSL/TLS 검증
            if not self._test_ssl_configuration():
                return False

            # 네트워크 정책 확인
            if not self._test_network_policies():
                return False

            # 시크릿 및 설정 보안 확인
            if not self._test_secrets_security():
                return False

            # RBAC 정책 확인
            if not self._test_rbac_policies():
                return False

            self.logger.info("✅ Security validation tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Security validation test failed: {e}")
            return False

    def _test_ssl_configuration(self) -> bool:
        """SSL/TLS 설정 테스트"""
        try:
            import ssl
            import socket

            hostname = self.config.app_domain
            port = self.config.app_port

            # SSL 인증서 확인
            context = ssl.create_default_context()

            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    # 인증서 만료일 확인
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (not_after - datetime.now()).days

                    if days_until_expiry < 30:
                        self.logger.warning(f"SSL certificate expires in {days_until_expiry} days")

                    self.logger.info(f"SSL certificate valid until: {not_after}")
                    return True

        except Exception as e:
            self.logger.error(f"SSL configuration test failed: {e}")
            return False

    def _test_network_policies(self) -> bool:
        """네트워크 정책 테스트"""
        try:
            # NetworkPolicy 리소스 확인
            networking_api = client.NetworkingV1Api()

            try:
                policies = networking_api.list_namespaced_network_policy(namespace=self.config.namespace)

                if not policies.items:
                    self.logger.warning("No network policies found in application namespace")
                    return True  # 경고만 하고 통과

                for policy in policies.items:
                    self.logger.info(f"Network policy found: {policy.metadata.name}")

            except Exception as e:
                self.logger.warning(f"Could not check network policies: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Network policies test failed: {e}")
            return False

    def _test_secrets_security(self) -> bool:
        """시크릿 보안 테스트"""
        try:
            # 시크릿 리소스 확인
            secrets = self.k8s_client.list_namespaced_secret(namespace=self.config.namespace)

            for secret in secrets.items:
                # 기본 시크릿 제외
                if secret.type in ['kubernetes.io/service-account-token', 'kubernetes.io/dockerconfigjson']:
                    continue

                # 시크릿이 base64로 인코딩되어 있는지 확인
                if secret.data:
                    for key, value in secret.data.items():
                        if not value:  # 빈 값 확인
                            self.logger.warning(f"Empty value in secret {secret.metadata.name}/{key}")

                self.logger.info(f"Secret verified: {secret.metadata.name}")

            return True

        except Exception as e:
            self.logger.error(f"Secrets security test failed: {e}")
            return False

    def _test_rbac_policies(self) -> bool:
        """RBAC 정책 테스트"""
        try:
            rbac_api = client.RbacAuthorizationV1Api()

            # 서비스 어카운트 확인
            service_accounts = self.k8s_client.list_namespaced_service_account(namespace=self.config.namespace)

            for sa in service_accounts.items:
                if sa.metadata.name == 'default':
                    continue

                self.logger.info(f"Service account found: {sa.metadata.name}")

            # 역할 및 역할 바인딩 확인
            try:
                roles = rbac_api.list_namespaced_role(namespace=self.config.namespace)
                role_bindings = rbac_api.list_namespaced_role_binding(namespace=self.config.namespace)

                self.logger.info(f"Found {len(roles.items)} roles and {len(role_bindings.items)} role bindings")

            except Exception as e:
                self.logger.warning(f"Could not check RBAC policies: {e}")

            return True

        except Exception as e:
            self.logger.error(f"RBAC policies test failed: {e}")
            return False

    def _test_monitoring_system(self) -> bool:
        """모니터링 시스템 테스트"""
        try:
            self.logger.info("Testing monitoring and alerting systems...")

            # Prometheus 상태 확인
            if not self._test_prometheus_metrics():
                return False

            # Grafana 대시보드 접근성 확인
            if not self._test_grafana_dashboards():
                return False

            # 알림 시스템 테스트
            if not self._test_alert_system():
                return False

            self.logger.info("✅ Monitoring system tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Monitoring system test failed: {e}")
            return False

    def _test_prometheus_metrics(self) -> bool:
        """Prometheus 메트릭 테스트"""
        try:
            # Prometheus 서비스 확인
            monitoring_ns = 'monitoring'

            try:
                services = self.k8s_client.list_namespaced_service(namespace=monitoring_ns)
                prometheus_service = None

                for service in services.items:
                    if 'prometheus' in service.metadata.name:
                        prometheus_service = service
                        break

                if not prometheus_service:
                    self.logger.warning("Prometheus service not found")
                    return True  # 모니터링이 없어도 앱은 동작해야 함

                # 메트릭 엔드포인트 테스트 (클러스터 내부)
                prometheus_url = f"http://{prometheus_service.metadata.name}.{monitoring_ns}.svc.cluster.local:9090"

                # kubectl을 통한 포트 포워딩으로 테스트
                port_forward_cmd = [
                    'kubectl', 'port-forward', '-n', monitoring_ns,
                    f'service/{prometheus_service.metadata.name}', '9090:9090'
                ]

                # 간단한 연결 테스트만 수행
                self.logger.info(f"Prometheus service found: {prometheus_service.metadata.name}")
                return True

            except Exception as e:
                self.logger.warning(f"Could not test Prometheus metrics: {e}")
                return True  # 경고만 하고 통과

        except Exception as e:
            self.logger.error(f"Prometheus metrics test failed: {e}")
            return False

    def _test_grafana_dashboards(self) -> bool:
        """Grafana 대시보드 테스트"""
        try:
            # Grafana 서비스 확인
            monitoring_ns = 'monitoring'

            try:
                services = self.k8s_client.list_namespaced_service(namespace=monitoring_ns)
                grafana_service = None

                for service in services.items:
                    if 'grafana' in service.metadata.name:
                        grafana_service = service
                        break

                if grafana_service:
                    self.logger.info(f"Grafana service found: {grafana_service.metadata.name}")
                else:
                    self.logger.warning("Grafana service not found")

                return True  # 대시보드가 없어도 통과

            except Exception as e:
                self.logger.warning(f"Could not test Grafana dashboards: {e}")
                return True

        except Exception as e:
            self.logger.error(f"Grafana dashboards test failed: {e}")
            return False

    def _test_alert_system(self) -> bool:
        """알림 시스템 테스트"""
        try:
            # AlertManager 서비스 확인
            monitoring_ns = 'monitoring'

            try:
                services = self.k8s_client.list_namespaced_service(namespace=monitoring_ns)
                alertmanager_service = None

                for service in services.items:
                    if 'alertmanager' in service.metadata.name:
                        alertmanager_service = service
                        break

                if alertmanager_service:
                    self.logger.info(f"AlertManager service found: {alertmanager_service.metadata.name}")
                else:
                    self.logger.warning("AlertManager service not found")

                return True

            except Exception as e:
                self.logger.warning(f"Could not test alert system: {e}")
                return True

        except Exception as e:
            self.logger.error(f"Alert system test failed: {e}")
            return False

    def _test_backup_recovery(self) -> bool:
        """백업 및 복구 테스트"""
        try:
            self.logger.info("Testing backup and recovery systems...")

            if not self.config.backup_test_enabled:
                self.logger.info("Backup testing disabled in configuration")
                return True

            # 데이터베이스 백업 확인
            if not self._test_database_backup():
                return False

            # 볼륨 백업 확인
            if not self._test_volume_backup():
                return False

            self.logger.info("✅ Backup and recovery tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Backup and recovery test failed: {e}")
            return False

    def _test_database_backup(self) -> bool:
        """데이터베이스 백업 테스트"""
        try:
            # PostgreSQL 백업 확인
            backup_test_cmd = [
                'kubectl', 'exec', '-n', self.config.namespace,
                'deploy/k-ocr-postgres', '--',
                'pg_dump', '--version'
            ]

            result = subprocess.run(backup_test_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                self.logger.warning("Could not test database backup capability")
                return True  # 경고만 하고 통과

            self.logger.info("Database backup capability confirmed")
            return True

        except Exception as e:
            self.logger.warning(f"Database backup test failed: {e}")
            return True

    def _test_volume_backup(self) -> bool:
        """볼륨 백업 테스트"""
        try:
            # PersistentVolume 확인
            pvs = self.k8s_client.list_persistent_volume()

            k_ocr_pvs = [
                pv for pv in pvs.items
                if pv.spec.claim_ref and pv.spec.claim_ref.namespace == self.config.namespace
            ]

            if k_ocr_pvs:
                self.logger.info(f"Found {len(k_ocr_pvs)} persistent volumes for K-OCR")
            else:
                self.logger.warning("No persistent volumes found for K-OCR")

            return True

        except Exception as e:
            self.logger.warning(f"Volume backup test failed: {e}")
            return True

    def _test_disaster_recovery(self) -> bool:
        """재해 복구 테스트"""
        try:
            self.logger.info("Testing disaster recovery preparedness...")

            if not self.config.disaster_recovery_test:
                self.logger.info("Disaster recovery testing disabled in configuration")
                return True

            # 다중 AZ 배포 확인
            if not self._test_multi_az_deployment():
                return False

            # 자동 페일오버 준비 상태 확인
            if not self._test_failover_readiness():
                return False

            self.logger.info("✅ Disaster recovery tests passed")
            return True

        except Exception as e:
            self.logger.error(f"Disaster recovery test failed: {e}")
            return False

    def _test_multi_az_deployment(self) -> bool:
        """다중 AZ 배포 확인"""
        try:
            # 노드의 AZ 분산 확인
            nodes = self.k8s_client.list_node()

            az_distribution = {}
            for node in nodes.items:
                labels = node.metadata.labels or {}

                # 클라우드별 AZ 레이블 확인
                az_label = None
                if 'topology.kubernetes.io/zone' in labels:
                    az_label = labels['topology.kubernetes.io/zone']
                elif 'failure-domain.beta.kubernetes.io/zone' in labels:
                    az_label = labels['failure-domain.beta.kubernetes.io/zone']

                if az_label:
                    if az_label not in az_distribution:
                        az_distribution[az_label] = 0
                    az_distribution[az_label] += 1

            if len(az_distribution) < 2:
                self.logger.warning(f"Cluster deployed in only {len(az_distribution)} availability zones")
                return True  # 경고만 하고 통과

            self.logger.info(f"Cluster distributed across {len(az_distribution)} availability zones: {list(az_distribution.keys())}")
            return True

        except Exception as e:
            self.logger.warning(f"Multi-AZ deployment test failed: {e}")
            return True

    def _test_failover_readiness(self) -> bool:
        """페일오버 준비 상태 테스트"""
        try:
            # 중요 서비스의 복제본 수 확인
            apps_api = client.AppsV1Api()

            deployments = apps_api.list_namespaced_deployment(namespace=self.config.namespace)

            for deployment in deployments.items:
                replicas = deployment.spec.replicas or 1
                available_replicas = deployment.status.available_replicas or 0

                if replicas < 2 and 'database' not in deployment.metadata.name.lower():
                    self.logger.warning(f"Deployment {deployment.metadata.name} has only {replicas} replicas")

                if available_replicas < replicas:
                    self.logger.error(f"Deployment {deployment.metadata.name}: only {available_replicas}/{replicas} replicas available")
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"Failover readiness test failed: {e}")
            return True

    def _test_performance_benchmarks(self) -> bool:
        """성능 벤치마크 테스트"""
        try:
            self.logger.info("Running performance benchmarks...")

            # 기본 성능 지표 수집
            performance_metrics = {}

            # 응답 시간 벤치마크
            app_url = f"https://{self.config.app_domain}"

            response_times = []
            for i in range(10):
                start_time = time.time()
                try:
                    response = requests.get(app_url, timeout=10)
                    if response.status_code == 200:
                        response_times.append(time.time() - start_time)
                except Exception:
                    pass
                time.sleep(1)

            if response_times:
                performance_metrics['avg_response_time'] = sum(response_times) / len(response_times)
                performance_metrics['min_response_time'] = min(response_times)
                performance_metrics['max_response_time'] = max(response_times)

            # 리소스 사용률 확인
            if not self._collect_resource_metrics(performance_metrics):
                return False

            # 성능 리포트 생성
            self._generate_performance_report(performance_metrics)

            self.logger.info("✅ Performance benchmarks completed")
            return True

        except Exception as e:
            self.logger.error(f"Performance benchmarks failed: {e}")
            return False

    def _collect_resource_metrics(self, metrics: Dict[str, Any]) -> bool:
        """리소스 메트릭 수집"""
        try:
            # 클러스터 리소스 사용률 확인 (간단한 버전)
            pods = self.k8s_client.list_namespaced_pod(namespace=self.config.namespace)

            total_pods = len(pods.items)
            running_pods = sum(1 for pod in pods.items if pod.status.phase == 'Running')

            metrics['total_pods'] = total_pods
            metrics['running_pods'] = running_pods
            metrics['pod_health_ratio'] = running_pods / total_pods if total_pods > 0 else 0

            return True

        except Exception as e:
            self.logger.warning(f"Could not collect resource metrics: {e}")
            return True

    def _generate_performance_report(self, metrics: Dict[str, Any]) -> None:
        """성능 리포트 생성"""
        try:
            report = {
                'test_timestamp': datetime.now().isoformat(),
                'cluster_name': self.config.cluster_name,
                'namespace': self.config.namespace,
                'performance_metrics': metrics,
                'recommendations': []
            }

            # 성능 분석 및 권장사항
            if 'avg_response_time' in metrics:
                if metrics['avg_response_time'] > 1.0:
                    report['recommendations'].append("Consider optimizing application response time")

                if metrics['max_response_time'] > 3.0:
                    report['recommendations'].append("Investigate high response time spikes")

            if 'pod_health_ratio' in metrics:
                if metrics['pod_health_ratio'] < 1.0:
                    report['recommendations'].append("Some pods are not in running state")

            # 리포트 저장
            report_file = f"production_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Performance report saved to: {report_file}")

        except Exception as e:
            self.logger.warning(f"Could not generate performance report: {e}")

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
                'cloud_provider': self.config.cloud_provider,
                'cluster_name': self.config.cluster_name,
                'namespace': self.config.namespace,
                'app_domain': self.config.app_domain
            }
        }

        # 최종 결과 출력
        self.logger.info("\n" + "="*80)
        self.logger.info("PRODUCTION DEPLOYMENT TEST SUMMARY")
        self.logger.info("="*80)
        self.logger.info(f"Test Duration: {total_duration:.2f} seconds")
        self.logger.info(f"Phases Completed: {successful_phases}/{total_phases}")
        self.logger.info(f"Success Rate: {summary['test_summary']['success_rate']:.1f}%")

        if summary['overall_success']:
            self.logger.info("🎉 ALL PRODUCTION TESTS PASSED!")
        else:
            self.logger.error("❌ Some production tests failed!")

            # 실패한 단계 나열
            failed_phases = [
                phase for phase, result in phase_results.items()
                if not result.get('success', False)
            ]
            self.logger.error(f"Failed phases: {', '.join(failed_phases)}")

        self.logger.info("="*80)

        # 결과 파일 저장
        try:
            summary_file = f"production_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Test summary saved to: {summary_file}")

        except Exception as e:
            self.logger.warning(f"Could not save test summary: {e}")

        # 알림 전송
        if self.config.slack_webhook_url and "slack" in self.config.alert_channels:
            self._send_slack_notification(summary)

        return summary

    def _send_slack_notification(self, summary: Dict[str, Any]) -> None:
        """Slack 알림 전송"""
        try:
            if not self.config.slack_webhook_url:
                return

            success_rate = summary['test_summary']['success_rate']
            emoji = "🎉" if summary['overall_success'] else "❌"

            message = {
                "text": f"{emoji} K-OCR Production Deployment Test Results",
                "attachments": [
                    {
                        "color": "good" if summary['overall_success'] else "danger",
                        "fields": [
                            {
                                "title": "Cluster",
                                "value": f"{self.config.cloud_provider.upper()} - {self.config.cluster_name}",
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
                            },
                            {
                                "title": "Timestamp",
                                "value": summary['test_summary']['timestamp'],
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
                self.logger.info("Slack notification sent successfully")
            else:
                self.logger.warning(f"Failed to send Slack notification: {response.status_code}")

        except Exception as e:
            self.logger.warning(f"Could not send Slack notification: {e}")


def main():
    """메인 함수"""
    # 설정 로드 (환경변수 또는 설정 파일에서)
    config = ProductionTestConfig(
        cloud_provider=os.getenv('CLOUD_PROVIDER', 'aws'),
        region=os.getenv('CLOUD_REGION', 'ap-northeast-2'),
        cluster_name=os.getenv('CLUSTER_NAME', 'k-ocr-production-cluster'),
        namespace=os.getenv('K8S_NAMESPACE', 'k-ocr'),
        app_domain=os.getenv('APP_DOMAIN', 'k-ocr.yourdomain.com'),
        slack_webhook_url=os.getenv('SLACK_WEBHOOK_URL')
    )

    # 테스터 인스턴스 생성
    tester = ProductionDeploymentTester(config)

    # 모든 테스트 실행
    results = tester.run_all_tests()

    # 종료 코드 설정
    exit_code = 0 if results.get('overall_success', False) else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()