#!/usr/bin/env python3
"""
K-OCR Web Corrector - 스테이징 환경 배포 테스트
스테이징 환경에서의 배포 및 통합 테스트
"""

import os
import sys
import time
import json
import subprocess
import requests
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from kubernetes import client, config
import boto3
from google.cloud import container_v1
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StagingDeploymentTester:
    """스테이징 환경 배포 테스터"""

    def __init__(self, cloud_provider: str = 'aws', config_path: str = None):
        """
        스테이징 테스터 초기화

        Args:
            cloud_provider: 클라우드 제공업체 ('aws', 'gcp', 'azure')
            config_path: 설정 파일 경로
        """
        self.cloud_provider = cloud_provider.lower()
        self.config_path = Path(config_path or os.getcwd())
        self.namespace = 'k-ocr-staging'
        self.test_results: List[Dict] = []
        self.deployment_info: Dict = {}

        # Kubernetes 클라이언트 초기화
        self._init_k8s_client()

        # 클라우드 클라이언트 초기화
        self._init_cloud_client()

    def _init_k8s_client(self):
        """Kubernetes 클라이언트 초기화"""
        try:
            # kubectl 설정 로드
            config.load_kube_config()
            self.k8s_apps_v1 = client.AppsV1Api()
            self.k8s_core_v1 = client.CoreV1Api()
            self.k8s_networking_v1 = client.NetworkingV1Api()
            logger.info("Kubernetes 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"Kubernetes 클라이언트 초기화 실패: {e}")
            raise

    def _init_cloud_client(self):
        """클라우드 클라이언트 초기화"""
        try:
            if self.cloud_provider == 'aws':
                self.cloud_client = boto3.client('ecs')
                self.ec2_client = boto3.client('ec2')
                self.rds_client = boto3.client('rds')
            elif self.cloud_provider == 'gcp':
                self.cloud_client = container_v1.ClusterManagerClient()
            elif self.cloud_provider == 'azure':
                credential = DefaultAzureCredential()
                self.cloud_client = ContainerServiceClient(credential, subscription_id=os.getenv('AZURE_SUBSCRIPTION_ID'))

            logger.info(f"{self.cloud_provider.upper()} 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"클라우드 클라이언트 초기화 실패: {e}")

    def run_all_tests(self) -> bool:
        """전체 테스트 실행"""
        logger.info("=== 스테이징 환경 배포 테스트 시작 ===")

        try:
            # 1. 인프라 상태 확인
            if not self._validate_infrastructure():
                return False

            # 2. 배포 실행
            if not self._deploy_to_staging():
                return False

            # 3. 배포 상태 확인
            if not self._validate_deployment():
                return False

            # 4. 서비스 헬스 체크
            if not self._health_check_services():
                return False

            # 5. E2E 테스트
            if not self._run_e2e_tests():
                return False

            # 6. 부하 테스트
            if not self._run_load_tests():
                return False

            # 7. 보안 테스트
            if not self._run_security_tests():
                return False

            # 8. 모니터링 검증
            if not self._validate_monitoring():
                return False

            logger.info("=== 스테이징 배포 테스트 성공 ===")
            self._generate_test_report()
            return True

        except Exception as e:
            logger.error(f"스테이징 테스트 실행 중 오류: {e}")
            return False

    def _validate_infrastructure(self) -> bool:
        """인프라 상태 검증"""
        logger.info("인프라 상태 검증 중...")

        try:
            if self.cloud_provider == 'aws':
                return self._validate_aws_infrastructure()
            elif self.cloud_provider == 'gcp':
                return self._validate_gcp_infrastructure()
            elif self.cloud_provider == 'azure':
                return self._validate_azure_infrastructure()
            else:
                logger.error(f"지원하지 않는 클라우드 제공업체: {self.cloud_provider}")
                return False

        except Exception as e:
            logger.error(f"인프라 검증 실패: {e}")
            return False

    def _validate_aws_infrastructure(self) -> bool:
        """AWS 인프라 검증"""
        logger.info("AWS 인프라 검증 중...")

        try:
            # EKS 클러스터 상태 확인
            eks_client = boto3.client('eks')
            cluster_name = 'k-ocr-staging-cluster'

            cluster_info = eks_client.describe_cluster(name=cluster_name)
            cluster_status = cluster_info['cluster']['status']

            if cluster_status != 'ACTIVE':
                logger.error(f"EKS 클러스터 상태 비정상: {cluster_status}")
                return False

            # RDS 인스턴스 상태 확인
            db_instances = self.rds_client.describe_db_instances()
            staging_dbs = [db for db in db_instances['DBInstances']
                          if 'staging' in db['DBInstanceIdentifier']]

            if not staging_dbs:
                logger.error("스테이징 RDS 인스턴스를 찾을 수 없습니다")
                return False

            for db in staging_dbs:
                if db['DBInstanceStatus'] != 'available':
                    logger.error(f"RDS 인스턴스 상태 비정상: {db['DBInstanceStatus']}")
                    return False

            # ElastiCache 상태 확인
            elasticache_client = boto3.client('elasticache')
            cache_clusters = elasticache_client.describe_cache_clusters()
            staging_caches = [cache for cache in cache_clusters['CacheClusters']
                             if 'staging' in cache['CacheClusterId']]

            for cache in staging_caches:
                if cache['CacheClusterStatus'] != 'available':
                    logger.error(f"ElastiCache 상태 비정상: {cache['CacheClusterStatus']}")
                    return False

            logger.info("AWS 인프라 검증 완료")
            return True

        except Exception as e:
            logger.error(f"AWS 인프라 검증 실패: {e}")
            return False

    def _validate_gcp_infrastructure(self) -> bool:
        """GCP 인프라 검증"""
        logger.info("GCP 인프라 검증 중...")

        try:
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            location = os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
            cluster_name = 'k-ocr-staging-cluster'

            # GKE 클러스터 상태 확인
            cluster_path = f"projects/{project_id}/locations/{location}/clusters/{cluster_name}"
            cluster = self.cloud_client.get_cluster(name=cluster_path)

            if cluster.status != container_v1.Cluster.Status.RUNNING:
                logger.error(f"GKE 클러스터 상태 비정상: {cluster.status}")
                return False

            logger.info("GCP 인프라 검증 완료")
            return True

        except Exception as e:
            logger.error(f"GCP 인프라 검증 실패: {e}")
            return False

    def _validate_azure_infrastructure(self) -> bool:
        """Azure 인프라 검증"""
        logger.info("Azure 인프라 검증 중...")

        try:
            resource_group = os.getenv('AZURE_RESOURCE_GROUP', 'k-ocr-staging-rg')
            cluster_name = 'k-ocr-staging-aks'

            # AKS 클러스터 상태 확인
            cluster = self.cloud_client.managed_clusters.get(
                resource_group_name=resource_group,
                resource_name=cluster_name
            )

            if cluster.provisioning_state != 'Succeeded':
                logger.error(f"AKS 클러스터 상태 비정상: {cluster.provisioning_state}")
                return False

            logger.info("Azure 인프라 검증 완료")
            return True

        except Exception as e:
            logger.error(f"Azure 인프라 검증 실패: {e}")
            return False

    def _deploy_to_staging(self) -> bool:
        """스테이징 환경에 배포"""
        logger.info("스테이징 환경 배포 중...")

        try:
            # 네임스페이스 생성
            self._create_namespace()

            # Kubernetes 매니페스트 적용
            manifest_files = [
                'deploy/kubernetes/base/namespace.yaml',
                'deploy/kubernetes/base/configmap.yaml',
                'deploy/kubernetes/base/secret.yaml',
                'deploy/kubernetes/base/pvc.yaml',
                'deploy/kubernetes/base/postgres.yaml',
                'deploy/kubernetes/base/redis.yaml',
                'deploy/kubernetes/base/web.yaml',
                'deploy/kubernetes/base/worker.yaml',
                'deploy/kubernetes/base/ingress.yaml',
                'deploy/autoscaling/hpa.yaml',
                'deploy/monitoring/prometheus.yaml',
            ]

            for manifest_file in manifest_files:
                manifest_path = self.config_path / manifest_file
                if manifest_path.exists():
                    self._apply_manifest(manifest_path)
                else:
                    logger.warning(f"매니페스트 파일 없음: {manifest_file}")

            # 배포 완료 대기
            if not self._wait_for_deployment():
                return False

            logger.info("스테이징 환경 배포 완료")
            return True

        except Exception as e:
            logger.error(f"배포 실패: {e}")
            return False

    def _create_namespace(self):
        """네임스페이스 생성"""
        try:
            namespace = client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=self.namespace,
                    labels={'environment': 'staging', 'app': 'k-ocr'}
                )
            )
            self.k8s_core_v1.create_namespace(namespace)
            logger.info(f"네임스페이스 생성: {self.namespace}")
        except client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"네임스페이스 이미 존재: {self.namespace}")
            else:
                raise

    def _apply_manifest(self, manifest_path: Path):
        """Kubernetes 매니페스트 적용"""
        logger.info(f"매니페스트 적용: {manifest_path}")

        try:
            result = subprocess.run([
                'kubectl', 'apply', '-f', str(manifest_path),
                '-n', self.namespace
            ], capture_output=True, text=True, check=True)

            logger.info(f"매니페스트 적용 완료: {manifest_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"매니페스트 적용 실패: {manifest_path}, 오류: {e.stderr}")
            raise

    def _wait_for_deployment(self, timeout: int = 600) -> bool:
        """배포 완료 대기"""
        logger.info("배포 완료 대기 중...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # 모든 Deployment 상태 확인
                deployments = self.k8s_apps_v1.list_namespaced_deployment(
                    namespace=self.namespace
                )

                all_ready = True
                for deployment in deployments.items:
                    if deployment.status.ready_replicas != deployment.spec.replicas:
                        all_ready = False
                        logger.info(f"배포 대기: {deployment.metadata.name} "
                                  f"({deployment.status.ready_replicas}/{deployment.spec.replicas})")
                        break

                if all_ready and deployments.items:
                    logger.info("모든 배포 완료")
                    return True

                time.sleep(30)

            except Exception as e:
                logger.error(f"배포 상태 확인 오류: {e}")
                time.sleep(30)

        logger.error("배포 완료 타임아웃")
        return False

    def _validate_deployment(self) -> bool:
        """배포 상태 검증"""
        logger.info("배포 상태 검증 중...")

        try:
            # Pod 상태 확인
            pods = self.k8s_core_v1.list_namespaced_pod(namespace=self.namespace)

            running_pods = 0
            total_pods = len(pods.items)

            for pod in pods.items:
                if pod.status.phase == 'Running':
                    running_pods += 1
                else:
                    logger.warning(f"Pod 상태 비정상: {pod.metadata.name} - {pod.status.phase}")

            success_rate = running_pods / total_pods if total_pods > 0 else 0
            logger.info(f"Pod 상태: {running_pods}/{total_pods} Running ({success_rate:.1%})")

            # 서비스 상태 확인
            services = self.k8s_core_v1.list_namespaced_service(namespace=self.namespace)
            logger.info(f"서비스 개수: {len(services.items)}")

            # Ingress 상태 확인
            ingresses = self.k8s_networking_v1.list_namespaced_ingress(namespace=self.namespace)
            logger.info(f"Ingress 개수: {len(ingresses.items)}")

            self.test_results.append({
                'test': 'deployment_validation',
                'running_pods': running_pods,
                'total_pods': total_pods,
                'success_rate': success_rate,
                'services_count': len(services.items),
                'ingress_count': len(ingresses.items),
                'category': 'deployment'
            })

            return success_rate >= 0.8

        except Exception as e:
            logger.error(f"배포 검증 실패: {e}")
            return False

    def _health_check_services(self) -> bool:
        """서비스 헬스 체크"""
        logger.info("서비스 헬스 체크 중...")

        try:
            # Ingress 엔드포인트 찾기
            ingress_url = self._get_ingress_url()
            if not ingress_url:
                logger.error("Ingress URL을 찾을 수 없습니다")
                return False

            # 헬스 체크 엔드포인트 테스트
            health_endpoints = [
                f"{ingress_url}/api/download/health",
                f"{ingress_url}/",
            ]

            healthy_endpoints = 0
            for endpoint in health_endpoints:
                try:
                    response = requests.get(endpoint, timeout=30, verify=False)
                    if response.status_code == 200:
                        healthy_endpoints += 1
                        logger.info(f"✅ {endpoint} - OK")
                    else:
                        logger.warning(f"❌ {endpoint} - {response.status_code}")
                except Exception as e:
                    logger.warning(f"❌ {endpoint} - {e}")

            success_rate = healthy_endpoints / len(health_endpoints)
            logger.info(f"헬스 체크: {healthy_endpoints}/{len(health_endpoints)} 성공")

            self.test_results.append({
                'test': 'health_check',
                'healthy_endpoints': healthy_endpoints,
                'total_endpoints': len(health_endpoints),
                'success_rate': success_rate,
                'category': 'health'
            })

            return success_rate >= 0.5

        except Exception as e:
            logger.error(f"헬스 체크 실패: {e}")
            return False

    def _get_ingress_url(self) -> Optional[str]:
        """Ingress URL 획득"""
        try:
            ingresses = self.k8s_networking_v1.list_namespaced_ingress(
                namespace=self.namespace
            )

            for ingress in ingresses.items:
                if ingress.status.load_balancer and ingress.status.load_balancer.ingress:
                    lb_ingress = ingress.status.load_balancer.ingress[0]
                    if lb_ingress.hostname:
                        return f"https://{lb_ingress.hostname}"
                    elif lb_ingress.ip:
                        return f"http://{lb_ingress.ip}"

            return None

        except Exception as e:
            logger.error(f"Ingress URL 획득 실패: {e}")
            return None

    def _run_e2e_tests(self) -> bool:
        """E2E 테스트 실행"""
        logger.info("E2E 테스트 실행 중...")

        try:
            ingress_url = self._get_ingress_url()
            if not ingress_url:
                return False

            test_cases = [
                ("메인 페이지 로드", self._test_main_page_load, ingress_url),
                ("파일 업로드 폼", self._test_upload_form, ingress_url),
                ("API 문서", self._test_api_docs, ingress_url),
            ]

            passed = 0
            for test_name, test_func, *args in test_cases:
                try:
                    result = test_func(*args)
                    if result:
                        logger.info(f"✅ {test_name}")
                        passed += 1
                    else:
                        logger.error(f"❌ {test_name}")
                except Exception as e:
                    logger.error(f"❌ {test_name}: {e}")

            success_rate = passed / len(test_cases)
            logger.info(f"E2E 테스트: {passed}/{len(test_cases)} 성공")

            self.test_results.append({
                'test': 'e2e_tests',
                'passed': passed,
                'total': len(test_cases),
                'success_rate': success_rate,
                'category': 'e2e'
            })

            return success_rate >= 0.7

        except Exception as e:
            logger.error(f"E2E 테스트 실패: {e}")
            return False

    def _test_main_page_load(self, url: str) -> bool:
        """메인 페이지 로드 테스트"""
        try:
            response = requests.get(url, timeout=30, verify=False)
            return response.status_code == 200 and 'K-OCR' in response.text
        except Exception:
            return False

    def _test_upload_form(self, url: str) -> bool:
        """업로드 폼 테스트"""
        try:
            response = requests.get(url, timeout=30, verify=False)
            return response.status_code == 200 and 'upload' in response.text.lower()
        except Exception:
            return False

    def _test_api_docs(self, url: str) -> bool:
        """API 문서 테스트"""
        try:
            response = requests.get(f"{url}/api/docs", timeout=30, verify=False)
            return response.status_code == 200
        except Exception:
            return False

    def _run_load_tests(self) -> bool:
        """부하 테스트 실행"""
        logger.info("부하 테스트 실행 중...")

        try:
            ingress_url = self._get_ingress_url()
            if not ingress_url:
                return False

            # 간단한 부하 테스트 (동시 요청)
            import concurrent.futures

            def make_request():
                try:
                    response = requests.get(
                        f"{ingress_url}/api/download/health",
                        timeout=30,
                        verify=False
                    )
                    return response.status_code == 200
                except Exception:
                    return False

            # 20개 동시 요청
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                start_time = time.time()
                futures = [executor.submit(make_request) for _ in range(20)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                end_time = time.time()

            duration = end_time - start_time
            success_count = sum(results)
            success_rate = success_count / len(results)

            logger.info(f"부하 테스트: {success_count}/20 성공, {duration:.2f}초")

            self.test_results.append({
                'test': 'load_test',
                'requests': 20,
                'success_count': success_count,
                'success_rate': success_rate,
                'duration': duration,
                'category': 'performance'
            })

            return success_rate >= 0.8

        except Exception as e:
            logger.error(f"부하 테스트 실패: {e}")
            return False

    def _run_security_tests(self) -> bool:
        """보안 테스트 실행"""
        logger.info("보안 테스트 실행 중...")

        try:
            ingress_url = self._get_ingress_url()
            if not ingress_url:
                return False

            security_checks = 0
            total_checks = 3

            # HTTPS 리다이렉트 확인
            try:
                http_url = ingress_url.replace('https://', 'http://')
                response = requests.get(http_url, timeout=10, allow_redirects=False, verify=False)
                if response.status_code in [301, 302, 308]:
                    security_checks += 1
                    logger.info("✅ HTTPS 리다이렉트 확인")
            except Exception:
                logger.warning("❌ HTTPS 리다이렉트 확인 실패")

            # 보안 헤더 확인
            try:
                response = requests.get(ingress_url, timeout=10, verify=False)
                security_headers = [
                    'X-Content-Type-Options',
                    'X-Frame-Options',
                    'X-XSS-Protection'
                ]

                found_headers = sum(1 for header in security_headers
                                  if header in response.headers)

                if found_headers >= len(security_headers) // 2:
                    security_checks += 1
                    logger.info("✅ 보안 헤더 확인")
            except Exception:
                logger.warning("❌ 보안 헤더 확인 실패")

            # 비허가 엔드포인트 접근 차단 확인
            try:
                response = requests.get(f"{ingress_url}/admin", timeout=10, verify=False)
                if response.status_code in [401, 403, 404]:
                    security_checks += 1
                    logger.info("✅ 접근 차단 확인")
            except Exception:
                logger.warning("❌ 접근 차단 확인 실패")

            success_rate = security_checks / total_checks
            logger.info(f"보안 테스트: {security_checks}/{total_checks} 통과")

            self.test_results.append({
                'test': 'security_tests',
                'passed_checks': security_checks,
                'total_checks': total_checks,
                'success_rate': success_rate,
                'category': 'security'
            })

            return success_rate >= 0.6

        except Exception as e:
            logger.error(f"보안 테스트 실패: {e}")
            return False

    def _validate_monitoring(self) -> bool:
        """모니터링 검증"""
        logger.info("모니터링 시스템 검증 중...")

        try:
            # Prometheus 서비스 확인
            monitoring_services = ['prometheus', 'grafana', 'alertmanager']
            available_services = 0

            services = self.k8s_core_v1.list_namespaced_service(
                namespace='monitoring'
            )

            service_names = [svc.metadata.name for svc in services.items]

            for monitoring_service in monitoring_services:
                if any(monitoring_service in name for name in service_names):
                    available_services += 1
                    logger.info(f"✅ {monitoring_service} 서비스 확인")
                else:
                    logger.warning(f"❌ {monitoring_service} 서비스 없음")

            success_rate = available_services / len(monitoring_services)
            logger.info(f"모니터링 서비스: {available_services}/{len(monitoring_services)}")

            self.test_results.append({
                'test': 'monitoring_validation',
                'available_services': available_services,
                'total_services': len(monitoring_services),
                'success_rate': success_rate,
                'category': 'monitoring'
            })

            return success_rate >= 0.5

        except Exception as e:
            logger.error(f"모니터링 검증 실패: {e}")
            return False

    def _generate_test_report(self):
        """테스트 보고서 생성"""
        logger.info("테스트 보고서 생성 중...")

        # 카테고리별 결과 집계
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'tests': [], 'success_count': 0}

            categories[category]['tests'].append(result)
            if result.get('success_rate', 0) >= 0.5:
                categories[category]['success_count'] += 1

        # 전체 통계
        total_tests = len(self.test_results)
        total_passed = sum(1 for r in self.test_results if r.get('success_rate', 0) >= 0.5)

        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'environment': 'staging',
            'cloud_provider': self.cloud_provider,
            'namespace': self.namespace,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': total_passed,
                'success_rate': total_passed / total_tests if total_tests > 0 else 0
            },
            'categories': categories,
            'deployment_info': self.deployment_info,
            'test_results': self.test_results
        }

        # 보고서 저장
        report_file = self.config_path / 'deploy/tests/staging-test-report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"테스트 보고서 저장: {report_file}")
        logger.info(f"전체 결과: {total_passed}/{total_tests} 성공 ({total_passed/total_tests:.1%})")

    def cleanup_staging(self):
        """스테이징 환경 정리"""
        logger.info("스테이징 환경 정리 중...")

        try:
            # 네임스페이스 삭제 (모든 리소스와 함께)
            self.k8s_core_v1.delete_namespace(
                name=self.namespace,
                body=client.V1DeleteOptions()
            )
            logger.info(f"네임스페이스 삭제: {self.namespace}")

        except Exception as e:
            logger.error(f"정리 중 오류: {e}")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='K-OCR 스테이징 환경 배포 테스트')
    parser.add_argument('--cloud', '-c', choices=['aws', 'gcp', 'azure'],
                       default='aws', help='클라우드 제공업체')
    parser.add_argument('--config-path', '-p', help='설정 파일 경로')
    parser.add_argument('--cleanup', action='store_true',
                       help='테스트 후 정리')

    args = parser.parse_args()

    tester = StagingDeploymentTester(args.cloud, args.config_path)

    try:
        success = tester.run_all_tests()

        if not success:
            logger.error("스테이징 테스트 실패")
            sys.exit(1)

        logger.info("스테이징 테스트 성공!")

    finally:
        if args.cleanup:
            tester.cleanup_staging()


if __name__ == '__main__':
    main()