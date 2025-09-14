terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }

  backend "azurerm" {
    # Configure your Azure Storage backend
    # storage_account_name = "terraformstate"
    # container_name       = "tfstate"
    # key                  = "k-ocr-web-corrector/terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "azuread" {
}

# Variables
variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "k-ocr-rg"
}

variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "k-ocr-aks"
}

variable "node_count" {
  description = "Number of nodes in the AKS cluster"
  type        = number
  default     = 3
}

variable "vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# Local values
locals {
  name_prefix = "${var.environment}-k-ocr"
  common_tags = {
    Environment = var.environment
    Project     = "K-OCR Web Corrector"
    ManagedBy   = "Terraform"
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${local.name_prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

# Subnets
resource "azurerm_subnet" "aks" {
  name                 = "${local.name_prefix}-aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "aks-delegation"
    service_delegation {
      name    = "Microsoft.ContainerService/managedClusters"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "appgw" {
  name                 = "${local.name_prefix}-appgw-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_subnet" "db" {
  name                 = "${local.name_prefix}-db-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.3.0/24"]

  delegation {
    name = "db-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Network Security Groups
resource "azurerm_network_security_group" "aks" {
  name                = "${local.name_prefix}-aks-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags

  security_rule {
    name                       = "AllowHTTP"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}

# User Assigned Identity for AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${local.name_prefix}-aks-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

# Role assignments for AKS identity
resource "azurerm_role_assignment" "aks_network" {
  scope                = azurerm_virtual_network.main.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

resource "azurerm_role_assignment" "aks_acr" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# Azure Kubernetes Service
resource "azurerm_kubernetes_cluster" "main" {
  name                = var.cluster_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${local.name_prefix}-k8s"
  tags                = local.common_tags

  default_node_pool {
    name                = "default"
    node_count          = var.node_count
    vm_size             = var.vm_size
    vnet_subnet_id      = azurerm_subnet.aks.id
    type                = "VirtualMachineScaleSets"
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 10

    upgrade_settings {
      max_surge = "10%"
    }

    node_labels = {
      "nodepool" = "default"
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.1.0.0/16"
    dns_service_ip    = "10.1.0.10"
  }

  azure_policy_enabled = true

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  microsoft_defender {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  workload_identity_enabled = true
  oidc_issuer_enabled      = true

  maintenance_window {
    allowed {
      day   = "Sunday"
      hours = [2, 3, 4]
    }
  }

  auto_scaler_profile {
    balance_similar_node_groups      = false
    expander                        = "random"
    max_graceful_termination_sec    = "600"
    max_node_provisioning_time      = "15m"
    max_unready_nodes               = 3
    max_unready_percentage          = 45
    new_pod_scale_up_delay          = "10s"
    scale_down_delay_after_add      = "10m"
    scale_down_delay_after_delete   = "10s"
    scale_down_delay_after_failure  = "3m"
    scan_interval                   = "10s"
    scale_down_unneeded             = "10m"
    scale_down_unready              = "20m"
    scale_down_utilization_threshold = 0.5
  }
}

# Worker Node Pool for heavy workloads
resource "azurerm_kubernetes_cluster_node_pool" "worker" {
  name                  = "worker"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size              = "Standard_D8s_v3"
  node_count           = 2
  vnet_subnet_id       = azurerm_subnet.aks.id

  enable_auto_scaling = true
  min_count          = 1
  max_count          = 5

  node_labels = {
    "nodepool" = "worker"
    "workload" = "compute-intensive"
  }

  node_taints = [
    "workload=compute-intensive:NoSchedule"
  ]

  tags = local.common_tags
}

# Container Registry
resource "azurerm_container_registry" "main" {
  name                = "${replace(local.name_prefix, "-", "")}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = local.common_tags

  identity {
    type = "SystemAssigned"
  }

  encryption {
    enabled = true
  }

  retention_policy {
    days    = 7
    enabled = true
  }

  trust_policy {
    enabled = true
  }

  network_rule_set {
    default_action = "Allow"
  }
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${local.name_prefix}-postgres"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  delegated_subnet_id    = azurerm_subnet.db.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgres.id
  administrator_login    = "k_ocr_user"
  administrator_password = var.db_password

  zone = "1"

  storage_mb   = 102400  # 100GB
  storage_tier = "P6"

  sku_name = var.environment == "production" ? "GP_Standard_D4s_v3" : "GP_Standard_D2s_v3"

  backup_retention_days        = 7
  geo_redundant_backup_enabled = var.environment == "production" ? true : false

  high_availability {
    mode                      = var.environment == "production" ? "ZoneRedundant" : "SameZone"
    standby_availability_zone = var.environment == "production" ? "2" : "1"
  }

  maintenance_window {
    day_of_week  = 0  # Sunday
    start_hour   = 3
    start_minute = 0
  }

  tags = local.common_tags

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "k_ocr_db"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgres" {
  name                = "${local.name_prefix}-postgres.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${local.name_prefix}-postgres-vnet-link"
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.main.id
  resource_group_name   = azurerm_resource_group.main.name
  tags                  = local.common_tags
}

# Redis Cache
resource "azurerm_redis_cache" "main" {
  name                = "${local.name_prefix}-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 2
  family              = "C"
  sku_name            = "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  tags                = local.common_tags

  redis_configuration {
    enable_authentication           = true
    maxmemory_reserved              = 200
    maxmemory_delta                 = 200
    maxmemory_policy                = "allkeys-lru"
    notify_keyspace_events         = ""
    rdb_backup_enabled             = true
    rdb_backup_frequency           = 60
    rdb_backup_max_snapshot_count  = 1
    rdb_storage_connection_string  = azurerm_storage_account.main.primary_blob_connection_string
  }

  patch_schedule {
    day_of_week    = "Sunday"
    start_hour_utc = 3
  }
}

# Storage Account
resource "azurerm_storage_account" "main" {
  name                     = "${replace(local.name_prefix, "-", "")}storage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "production" ? "GRS" : "LRS"
  account_kind             = "StorageV2"
  access_tier              = "Hot"

  blob_properties {
    versioning_enabled       = true
    last_access_time_enabled = true
    change_feed_enabled      = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  tags = local.common_tags
}

resource "azurerm_storage_container" "temp" {
  name                  = "temp-files"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "models" {
  name                  = "ocr-models"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "main" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "temp-files-lifecycle"
    enabled = true

    filters {
      prefix_match = ["temp-files/"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 7
      }
    }
  }
}

# Public IP for Application Gateway
resource "azurerm_public_ip" "appgw" {
  name                = "${local.name_prefix}-appgw-pip"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.common_tags
}

# Application Gateway
resource "azurerm_application_gateway" "main" {
  name                = "${local.name_prefix}-appgw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.common_tags

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 2
  }

  gateway_ip_configuration {
    name      = "appgw-ip-configuration"
    subnet_id = azurerm_subnet.appgw.id
  }

  frontend_port {
    name = "http-port"
    port = 80
  }

  frontend_port {
    name = "https-port"
    port = 443
  }

  frontend_ip_configuration {
    name                 = "appgw-frontend-ip"
    public_ip_address_id = azurerm_public_ip.appgw.id
  }

  backend_address_pool {
    name = "aks-backend-pool"
  }

  backend_http_settings {
    name                  = "aks-http-settings"
    cookie_based_affinity = "Enabled"
    path                  = "/"
    port                  = 80
    protocol              = "Http"
    request_timeout       = 300

    probe_name = "aks-health-probe"
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "appgw-frontend-ip"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = "http-routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "aks-backend-pool"
    backend_http_settings_name = "aks-http-settings"
    priority                   = 100
  }

  probe {
    name                = "aks-health-probe"
    protocol            = "Http"
    path                = "/api/download/health"
    host                = "127.0.0.1"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3

    match {
      status_code = ["200"]
    }
  }

  autoscale_configuration {
    min_capacity = 2
    max_capacity = 10
  }

  waf_configuration {
    enabled          = true
    firewall_mode    = "Detection"
    rule_set_type    = "OWASP"
    rule_set_version = "3.2"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${local.name_prefix}-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.common_tags
}

# Key Vault
resource "azurerm_key_vault" "main" {
  name                = "${local.name_prefix}-kv"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  soft_delete_retention_days = 7
  purge_protection_enabled   = var.environment == "production" ? true : false

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  tags = local.common_tags
}

# Data source for current client config
data "azurerm_client_config" "current" {}

# Key Vault access policy for current user/service principal
resource "azurerm_key_vault_access_policy" "current" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# Key Vault access policy for AKS
resource "azurerm_key_vault_access_policy" "aks" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.aks.principal_id

  secret_permissions = [
    "Get", "List"
  ]
}

# Managed Identity for application pods
resource "azurerm_user_assigned_identity" "app" {
  name                = "${local.name_prefix}-app-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

# Federated identity credential for workload identity
resource "azurerm_federated_identity_credential" "app" {
  name                = "${local.name_prefix}-app-federated-credential"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.main.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.app.id
  subject             = "system:serviceaccount:k-ocr:k-ocr-service-account"
}

# Role assignments for app identity
resource "azurerm_role_assignment" "app_storage" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "app_keyvault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# Outputs
output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_cluster_fqdn" {
  description = "AKS cluster FQDN"
  value       = azurerm_kubernetes_cluster.main.fqdn
}

output "database_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "redis_hostname" {
  description = "Redis cache hostname"
  value       = azurerm_redis_cache.main.hostname
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.main.name
}

output "container_registry_login_server" {
  description = "Container registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "application_gateway_ip" {
  description = "Application Gateway public IP"
  value       = azurerm_public_ip.appgw.ip_address
}

output "app_identity_client_id" {
  description = "Application managed identity client ID"
  value       = azurerm_user_assigned_identity.app.client_id
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}