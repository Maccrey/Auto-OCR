terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # Configure your GCS backend
    # bucket = "your-terraform-state-bucket"
    # prefix = "k-ocr-web-corrector/terraform.tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "k-ocr-cluster"
}

variable "node_count" {
  description = "Number of nodes in the GKE cluster"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "e2-standard-4"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Local values
locals {
  name_prefix = "${var.environment}-k-ocr"
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "storage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com"
  ])

  project = var.project_id
  service = each.key
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "main" {
  name          = "${local.name_prefix}-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.main.id
  project       = var.project_id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${local.name_prefix}-allow-internal"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "${local.name_prefix}-allow-http-https"
  network = google_compute_network.main.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["http-server", "https-server"]
}

# GKE Cluster
resource "google_container_cluster" "main" {
  name     = var.cluster_name
  location = var.region
  project  = var.project_id

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  network    = google_compute_network.main.name
  subnetwork = google_compute_subnetwork.main.name

  # Configure IP allocation for VPC-native cluster
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Enable workload identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Enable network policy
  network_policy {
    enabled = true
  }

  # Enable binary authorization
  binary_authorization {
    evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  }

  # Enable monitoring and logging
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]

    managed_prometheus {
      enabled = true
    }
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS", "API_SERVER"]
  }

  # Maintenance policy
  maintenance_policy {
    recurring_window {
      start_time = "2024-01-01T02:00:00Z"
      end_time   = "2024-01-01T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SU"
    }
  }

  addons_config {
    horizontal_pod_autoscaling {
      disabled = false
    }

    http_load_balancing {
      disabled = false
    }

    network_policy_config {
      disabled = false
    }

    gcs_fuse_csi_driver_config {
      enabled = true
    }
  }

  depends_on = [google_project_service.apis]
}

# GKE Node Pool
resource "google_container_node_pool" "main" {
  name       = "${local.name_prefix}-node-pool"
  location   = var.region
  cluster    = google_container_cluster.main.name
  project    = var.project_id
  node_count = var.node_count

  autoscaling {
    min_node_count = 2
    max_node_count = 10
  }

  node_config {
    preemptible  = false
    machine_type = var.machine_type

    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_nodes.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      environment = var.environment
      project     = "k-ocr"
    }

    tags = ["k-ocr-node"]

    disk_size_gb = 100
    disk_type    = "pd-standard"

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }
}

# Service Accounts
resource "google_service_account" "gke_nodes" {
  account_id   = "${local.name_prefix}-gke-nodes"
  display_name = "GKE Nodes Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "gke_nodes" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer",
    "roles/storage.objectViewer",
    "roles/artifactregistry.reader"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_service_account" "k_ocr_app" {
  account_id   = "${local.name_prefix}-app"
  display_name = "K-OCR Application Service Account"
  project      = var.project_id
}

resource "google_project_iam_member" "k_ocr_app" {
  for_each = toset([
    "roles/storage.admin",
    "roles/cloudsql.client",
    "roles/redis.editor",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.k_ocr_app.email}"
}

# Enable workload identity binding
resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.k_ocr_app.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[k-ocr/k-ocr-service-account]"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = "${local.name_prefix}-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  settings {
    tier = "db-custom-2-4096"

    disk_size         = 100
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled       = false
      private_network    = google_compute_network.main.id
      allocated_ip_range = google_compute_global_address.private_ip_address.name
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }
  }

  deletion_protection = var.environment == "production"

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "database" {
  name     = "k_ocr_db"
  instance = google_sql_database_instance.main.name
  project  = var.project_id
}

resource "google_sql_user" "user" {
  name     = "k_ocr_user"
  instance = google_sql_database_instance.main.name
  password = var.db_password
  project  = var.project_id
}

# Private IP allocation for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "${local.name_prefix}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
  project       = var.project_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Redis Instance
resource "google_redis_instance" "main" {
  name           = "${local.name_prefix}-redis"
  tier           = "STANDARD_HA"
  memory_size_gb = 4
  region         = var.region
  project        = var.project_id

  location_id             = var.zone
  alternative_location_id = "${substr(var.region, 0, length(var.region) - 1)}b"

  authorized_network = google_compute_network.main.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_version     = "REDIS_7_0"
  display_name      = "${local.name_prefix} Redis"
  reserved_ip_range = "10.3.0.0/29"

  persistence_config {
    persistence_mode    = "RDB"
    rdb_snapshot_period = "ONE_HOUR"
  }

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }
}

# Cloud Storage Bucket
resource "google_storage_bucket" "main" {
  name     = "${local.name_prefix}-storage-${var.project_id}"
  location = var.region
  project  = var.project_id

  storage_class = "STANDARD"

  versioning {
    enabled = true
  }

  encryption {
    default_kms_key_name = google_kms_crypto_key.storage_key.id
  }

  lifecycle_rule {
    condition {
      age = 7
      matches_prefix = ["temp/"]
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      age                   = 30
      num_newer_versions    = 3
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis]
}

# Cloud KMS for encryption
resource "google_kms_key_ring" "main" {
  name     = "${local.name_prefix}-keyring"
  location = var.region
  project  = var.project_id

  depends_on = [google_project_service.apis]
}

resource "google_kms_crypto_key" "storage_key" {
  name     = "${local.name_prefix}-storage-key"
  key_ring = google_kms_key_ring.main.id

  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Grant access to Cloud Storage bucket
resource "google_storage_bucket_iam_member" "app_access" {
  bucket = google_storage_bucket.main.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${google_service_account.k_ocr_app.email}"
}

# Container Registry
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "k-ocr-images"
  description   = "K-OCR container images"
  format        = "DOCKER"
  project       = var.project_id

  depends_on = [google_project_service.apis]
}

# Secret Manager secrets
resource "google_secret_manager_secret" "app_secrets" {
  for_each = toset([
    "secret-key",
    "postgres-password",
    "service-account-json"
  ])

  secret_id = "k-ocr-${each.key}"
  project   = var.project_id

  replication {
    automatic = true
  }

  depends_on = [google_project_service.apis]
}

# Global Static IP for Ingress
resource "google_compute_global_address" "ingress_ip" {
  name    = "${local.name_prefix}-ip"
  project = var.project_id
}

# Cloud Armor security policy
resource "google_compute_security_policy" "main" {
  name    = "${local.name_prefix}-armor-policy"
  project = var.project_id

  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["192.0.2.0/24"] # Example blocked IP range
      }
    }
  }

  rule {
    action   = "rate_based_ban"
    priority = "2000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      ban_duration_sec = 300
    }
  }

  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}

# Filestore for shared storage
resource "google_filestore_instance" "main" {
  name     = "${local.name_prefix}-filestore"
  location = var.zone
  tier     = "STANDARD"
  project  = var.project_id

  file_shares {
    capacity_gb = 1024
    name        = "k_ocr_share"
  }

  networks {
    network = google_compute_network.main.name
    modes   = ["MODE_IPV4"]
  }
}

# Outputs
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.main.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.main.endpoint
  sensitive   = true
}

output "database_connection_name" {
  description = "Cloud SQL connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "database_private_ip" {
  description = "Cloud SQL private IP"
  value       = google_sql_database_instance.main.private_ip_address
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.main.host
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.main.port
}

output "storage_bucket_name" {
  description = "Cloud Storage bucket name"
  value       = google_storage_bucket.main.name
}

output "ingress_ip" {
  description = "Global static IP for ingress"
  value       = google_compute_global_address.ingress_ip.address
}

output "service_account_email" {
  description = "Application service account email"
  value       = google_service_account.k_ocr_app.email
}

output "artifact_registry_url" {
  description = "Artifact Registry URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}"
}