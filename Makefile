# K-OCR Web Corrector - Docker Management Makefile

.PHONY: help build dev prod test clean logs shell

# Variables
PROJECT_NAME = k-ocr-web-corrector
DEV_COMPOSE = docker-compose -f docker-compose.dev.yml
PROD_COMPOSE = docker-compose -f docker-compose.yml

# Default target
help: ## Show this help message
	@echo "K-OCR Web Corrector - Docker Management"
	@echo "========================================"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Development Environment
dev: ## Start development environment
	@echo "🚀 Starting development environment..."
	$(DEV_COMPOSE) up --build

dev-d: ## Start development environment in background
	@echo "🚀 Starting development environment (background)..."
	$(DEV_COMPOSE) up -d --build

dev-stop: ## Stop development environment
	@echo "⏹️ Stopping development environment..."
	$(DEV_COMPOSE) down

dev-logs: ## Show development logs
	@echo "📋 Development logs..."
	$(DEV_COMPOSE) logs -f

dev-shell: ## Access development web container shell
	@echo "🐚 Accessing development web container..."
	$(DEV_COMPOSE) exec web bash

# Production Environment
prod: ## Start production environment
	@echo "🚀 Starting production environment..."
	$(PROD_COMPOSE) --profile production up --build

prod-d: ## Start production environment in background
	@echo "🚀 Starting production environment (background)..."
	$(PROD_COMPOSE) --profile production up -d --build

prod-stop: ## Stop production environment
	@echo "⏹️ Stopping production environment..."
	$(PROD_COMPOSE) down

prod-logs: ## Show production logs
	@echo "📋 Production logs..."
	$(PROD_COMPOSE) logs -f

# Monitoring
monitoring: ## Start with monitoring stack (Prometheus + Grafana)
	@echo "📊 Starting with monitoring stack..."
	$(PROD_COMPOSE) --profile monitoring up -d

monitoring-stop: ## Stop monitoring services
	@echo "⏹️ Stopping monitoring services..."
	$(PROD_COMPOSE) --profile monitoring down

# Build Commands
build: ## Build all Docker images
	@echo "🔨 Building Docker images..."
	$(PROD_COMPOSE) build

build-dev: ## Build development images
	@echo "🔨 Building development images..."
	$(DEV_COMPOSE) build

build-prod: ## Build production images
	@echo "🔨 Building production images..."
	$(PROD_COMPOSE) build

build-nocache: ## Build without cache
	@echo "🔨 Building Docker images (no cache)..."
	$(PROD_COMPOSE) build --no-cache

# Testing
test: ## Run tests in container
	@echo "🧪 Running tests..."
	$(DEV_COMPOSE) run --rm web python -m pytest tests/ -v

test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	$(DEV_COMPOSE) run --rm web python -m pytest tests/test_integration/ -v

test-usability: ## Run usability tests (requires browser drivers)
	@echo "🧪 Running usability tests..."
	$(DEV_COMPOSE) run --rm web python -m pytest tests/test_usability/ -v

test-coverage: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	$(DEV_COMPOSE) run --rm web python -m pytest tests/ --cov=backend --cov-report=html

# Database Management
db-migrate: ## Run database migrations
	@echo "🗄️ Running database migrations..."
	$(DEV_COMPOSE) run --rm web alembic upgrade head

db-shell: ## Access database shell
	@echo "🗄️ Accessing database..."
	$(DEV_COMPOSE) exec postgres psql -U dev_user -d k_ocr_dev

# Maintenance
clean: ## Clean up containers, images, and volumes
	@echo "🧹 Cleaning up..."
	$(DEV_COMPOSE) down -v --remove-orphans
	$(PROD_COMPOSE) down -v --remove-orphans
	docker system prune -f

clean-all: ## Clean everything including images
	@echo "🧹 Deep cleaning..."
	$(DEV_COMPOSE) down -v --remove-orphans --rmi all
	$(PROD_COMPOSE) down -v --remove-orphans --rmi all
	docker system prune -af

# Logs and Debugging
logs: ## Show all logs
	@echo "📋 All service logs..."
	$(DEV_COMPOSE) logs -f

logs-web: ## Show web service logs
	@echo "📋 Web service logs..."
	$(DEV_COMPOSE) logs -f web

logs-worker: ## Show worker service logs
	@echo "📋 Worker service logs..."
	$(DEV_COMPOSE) logs -f worker

logs-redis: ## Show Redis logs
	@echo "📋 Redis logs..."
	$(DEV_COMPOSE) logs -f redis

# Health Checks
health: ## Run health check
	@echo "🏥 Running health check..."
	$(DEV_COMPOSE) exec web python scripts/health_check.py comprehensive

health-simple: ## Run simple health check
	@echo "🏥 Running simple health check..."
	$(DEV_COMPOSE) exec web python scripts/health_check.py simple

# Model Management
download-models: ## Download OCR models
	@echo "📥 Downloading OCR models..."
	$(DEV_COMPOSE) run --rm web python scripts/download_models.py

# Shell Access
shell-web: ## Access web container shell
	@echo "🐚 Accessing web container..."
	$(DEV_COMPOSE) exec web bash

shell-worker: ## Access worker container shell
	@echo "🐚 Accessing worker container..."
	$(DEV_COMPOSE) exec worker bash

shell-redis: ## Access Redis CLI
	@echo "🐚 Accessing Redis CLI..."
	$(DEV_COMPOSE) exec redis redis-cli

# Development Tools
format: ## Format code with black
	@echo "🎨 Formatting code..."
	$(DEV_COMPOSE) run --rm web black backend/ tests/

lint: ## Run linting
	@echo "🔍 Running linting..."
	$(DEV_COMPOSE) run --rm web flake8 backend/ tests/

type-check: ## Run type checking
	@echo "🔍 Running type check..."
	$(DEV_COMPOSE) run --rm web mypy backend/

# Backup and Restore
backup-db: ## Backup database
	@echo "💾 Backing up database..."
	$(DEV_COMPOSE) exec postgres pg_dump -U dev_user k_ocr_dev > backup_$$(date +%Y%m%d_%H%M%S).sql

# Security
security-scan: ## Run security scan (requires trivy)
	@echo "🔐 Running security scan..."
	trivy image $(PROJECT_NAME):latest

# Performance
benchmark: ## Run performance benchmark
	@echo "⚡ Running performance benchmark..."
	$(DEV_COMPOSE) run --rm web python -m pytest tests/test_integration/test_stress_and_load.py -v

# Environment Info
info: ## Show environment information
	@echo "ℹ️ Environment Information"
	@echo "=========================="
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker-compose --version)"
	@echo "Project: $(PROJECT_NAME)"
	@echo ""
	@echo "Available services:"
	@$(DEV_COMPOSE) config --services

status: ## Show service status
	@echo "📊 Service Status"
	@echo "================"
	@$(DEV_COMPOSE) ps

# Quick Start
quickstart: ## Quick start for development
	@echo "🚀 Quick start for development..."
	@echo "1. Building images..."
	@$(MAKE) build-dev
	@echo "2. Starting services..."
	@$(MAKE) dev-d
	@echo "3. Downloading models..."
	@sleep 10
	@$(MAKE) download-models
	@echo "4. Running health check..."
	@$(MAKE) health-simple
	@echo ""
	@echo "✅ Development environment is ready!"
	@echo "   Web UI: http://localhost:8000"
	@echo "   Flower: http://localhost:5555"
	@echo ""
	@echo "Use 'make logs' to see logs or 'make dev-stop' to stop."