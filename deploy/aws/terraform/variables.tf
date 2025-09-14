# AWS Configuration
variable "aws_region" {
  description = "AWS region where resources will be created"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "k-ocr-web-corrector"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage for RDS instance (GB)"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS instance (GB)"
  type        = number
  default     = 1000
}

variable "db_password" {
  description = "Password for the RDS database"
  type        = string
  sensitive   = true
}

variable "db_backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for RDS"
  type        = bool
  default     = true
}

# Cache Configuration
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

# ECS Configuration
variable "ecs_web_cpu" {
  description = "CPU units for web service (1024 = 1 vCPU)"
  type        = number
  default     = 2048
}

variable "ecs_web_memory" {
  description = "Memory for web service (MB)"
  type        = number
  default     = 4096
}

variable "ecs_web_desired_count" {
  description = "Desired number of web service tasks"
  type        = number
  default     = 3
}

variable "ecs_worker_cpu" {
  description = "CPU units for worker service (1024 = 1 vCPU)"
  type        = number
  default     = 4096
}

variable "ecs_worker_memory" {
  description = "Memory for worker service (MB)"
  type        = number
  default     = 8192
}

variable "ecs_worker_desired_count" {
  description = "Desired number of worker service tasks"
  type        = number
  default     = 2
}

# Auto Scaling Configuration
variable "autoscaling_enabled" {
  description = "Enable auto scaling for ECS services"
  type        = bool
  default     = true
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 2
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 10
}

variable "autoscaling_cpu_target" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "autoscaling_memory_target" {
  description = "Target memory utilization for auto scaling"
  type        = number
  default     = 80
}

# Load Balancer Configuration
variable "alb_enable_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = true
}

variable "alb_idle_timeout" {
  description = "ALB idle timeout in seconds"
  type        = number
  default     = 60
}

# SSL/TLS Configuration
variable "certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for domain"
  type        = string
  default     = ""
}

# Storage Configuration
variable "efs_throughput_mode" {
  description = "EFS throughput mode (provisioned or bursting)"
  type        = string
  default     = "provisioned"
}

variable "efs_provisioned_throughput_in_mibps" {
  description = "EFS provisioned throughput in MiB/s"
  type        = number
  default     = 100
}

variable "s3_lifecycle_temp_files_expiration_days" {
  description = "Days after which temporary files in S3 are deleted"
  type        = number
  default     = 7
}

# Monitoring Configuration
variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights for ECS cluster"
  type        = bool
  default     = true
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "enable_waf" {
  description = "Enable AWS WAF for the load balancer"
  type        = bool
  default     = true
}

# Backup Configuration
variable "enable_s3_versioning" {
  description = "Enable versioning for S3 bucket"
  type        = bool
  default     = true
}

variable "s3_backup_retention_days" {
  description = "S3 backup retention period in days"
  type        = number
  default     = 90
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Enable Fargate Spot instances for cost optimization"
  type        = bool
  default     = true
}

variable "spot_instance_percentage" {
  description = "Percentage of capacity to run on Spot instances (0-100)"
  type        = number
  default     = 80

  validation {
    condition     = var.spot_instance_percentage >= 0 && var.spot_instance_percentage <= 100
    error_message = "Spot instance percentage must be between 0 and 100."
  }
}

# Container Image Configuration
variable "container_image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}

variable "ecr_repository_url" {
  description = "ECR repository URL for container images"
  type        = string
  default     = ""
}

# Feature Flags
variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use a single NAT Gateway for cost optimization"
  type        = bool
  default     = false
}

# Notification Configuration
variable "notification_email" {
  description = "Email address for CloudWatch alarms and notifications"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
  sensitive   = true
}

# Resource Tagging
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Development/Testing Configuration
variable "enable_bastion_host" {
  description = "Enable bastion host for development access"
  type        = bool
  default     = false
}

variable "bastion_key_name" {
  description = "EC2 Key Pair name for bastion host"
  type        = string
  default     = ""
}

variable "developer_ip_addresses" {
  description = "List of developer IP addresses for bastion host access"
  type        = list(string)
  default     = []
}