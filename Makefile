.PHONY: help install dev prod test lint format migrate seed clean logs ps build

# ==============================================================================
# CONFIGURATION
# ==============================================================================
COMPOSE_DEV=docker compose -f infrastructure/docker/docker-compose.yml
COMPOSE_PROD=docker compose -f infrastructure/docker/docker-compose.prod.yml
BACKEND=apps/backend

# Colours
CYAN=\033[0;36m
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
NC=\033[0m

# ==============================================================================
# HELP
# ==============================================================================
help: ## Show this help
	@echo ""
	@echo "  $(CYAN)Encyklopedia Świętych Kościoła Katolickiego$(NC)"
	@echo "  ─────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ==============================================================================
# SETUP
# ==============================================================================
install: ## Install all dependencies (backend + frontend)
	@echo "$(CYAN)Installing backend dependencies...$(NC)"
	cd $(BACKEND) && pip install poetry && poetry install
	@echo "$(CYAN)Installing admin dependencies...$(NC)"
	cd apps/admin && npm install
	@echo "$(CYAN)Installing web dependencies...$(NC)"
	cd apps/web && npm install
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

setup: ## Initial project setup (copy .env, create dirs)
	@echo "$(CYAN)Setting up project...$(NC)"
	@if [ ! -f .env ]; then cp .env.example .env; echo "$(YELLOW)⚠ Created .env from .env.example – please update secrets!$(NC)"; fi
	@mkdir -p data/postgres data/redis data/minio logs
	@echo "$(GREEN)✓ Setup complete$(NC)"

# ==============================================================================
# DEVELOPMENT
# ==============================================================================
dev: ## Start all services in development mode
	$(COMPOSE_DEV) up

dev-build: ## Build and start all services in development mode
	$(COMPOSE_DEV) up --build

dev-backend: ## Start only backend services (db, redis, backend)
	$(COMPOSE_DEV) up db redis backend celery-worker

dev-db: ## Start only database
	$(COMPOSE_DEV) up db

dev-detach: ## Start all services in background
	$(COMPOSE_DEV) up -d

stop: ## Stop all development services
	$(COMPOSE_DEV) down

# ==============================================================================
# PRODUCTION
# ==============================================================================
prod-build: ## Build production images
	$(COMPOSE_PROD) build

prod-up: ## Start production stack
	$(COMPOSE_PROD) up -d

prod-down: ## Stop production stack
	$(COMPOSE_PROD) down

# ==============================================================================
# DATABASE
# ==============================================================================
migrate: ## Run Alembic migrations
	$(COMPOSE_DEV) exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	$(COMPOSE_DEV) exec backend alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	$(COMPOSE_DEV) exec backend alembic downgrade -1

migrate-history: ## Show migration history
	$(COMPOSE_DEV) exec backend alembic history

seed: ## Seed the database with initial data
	$(COMPOSE_DEV) exec backend python -m src.infrastructure.db.seed

reset-db: ## ⚠ Drop and recreate the database (DESTRUCTIVE!)
	@echo "$(RED)⚠ This will DESTROY all data! Press Ctrl+C to abort...$(NC)"
	@sleep 5
	$(COMPOSE_DEV) exec db psql -U $$POSTGRES_USER -c "DROP DATABASE IF EXISTS $$POSTGRES_DB;"
	$(COMPOSE_DEV) exec db psql -U $$POSTGRES_USER -c "CREATE DATABASE $$POSTGRES_DB;"
	$(MAKE) migrate
	$(MAKE) seed

# ==============================================================================
# TESTING
# ==============================================================================
test: ## Run all backend tests
	$(COMPOSE_DEV) run --rm backend pytest apps/backend/tests/ -v --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	$(COMPOSE_DEV) run --rm backend pytest apps/backend/tests/unit/ -v

test-integration: ## Run integration tests only
	$(COMPOSE_DEV) run --rm backend pytest apps/backend/tests/integration/ -v

test-e2e: ## Run E2E tests (Playwright)
	cd apps/admin && npx playwright test

test-coverage: ## Run tests with HTML coverage report
	$(COMPOSE_DEV) run --rm backend pytest apps/backend/tests/ --cov=src --cov-report=html:htmlcov

# ==============================================================================
# CODE QUALITY
# ==============================================================================
lint: ## Run linters (ruff + mypy + eslint)
	@echo "$(CYAN)Running Python linters...$(NC)"
	cd $(BACKEND) && poetry run ruff check src/ tests/
	cd $(BACKEND) && poetry run mypy src/
	@echo "$(CYAN)Running TypeScript linters...$(NC)"
	cd apps/admin && npm run lint
	cd apps/web && npm run lint

format: ## Auto-format all code (black + ruff + prettier)
	@echo "$(CYAN)Formatting Python code...$(NC)"
	cd $(BACKEND) && poetry run black src/ tests/
	cd $(BACKEND) && poetry run ruff check --fix src/ tests/
	@echo "$(CYAN)Formatting TypeScript code...$(NC)"
	cd apps/admin && npm run format
	cd apps/web && npm run format

type-check: ## Run TypeScript type checking
	cd apps/admin && npm run type-check
	cd apps/web && npm run type-check

# ==============================================================================
# UTILITIES
# ==============================================================================
logs: ## Show logs for all services
	$(COMPOSE_DEV) logs -f

logs-backend: ## Show backend logs
	$(COMPOSE_DEV) logs -f backend

logs-db: ## Show database logs
	$(COMPOSE_DEV) logs -f db

ps: ## Show running containers
	$(COMPOSE_DEV) ps

shell-backend: ## Open shell in backend container
	$(COMPOSE_DEV) exec backend bash

shell-db: ## Open PostgreSQL shell
	$(COMPOSE_DEV) exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

clean: ## Remove all containers, volumes, and build artifacts
	$(COMPOSE_DEV) down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

build: ## Build all Docker images
	$(COMPOSE_DEV) build

# ==============================================================================
# EXPORTS
# ==============================================================================
export-xlsx: ## Trigger Master.xlsx export
	$(COMPOSE_DEV) exec backend python -m scripts.export xlsx

export-pdf: ## Trigger Encyclopedia PDF export
	$(COMPOSE_DEV) exec backend python -m scripts.export pdf

# ==============================================================================
# DOCUMENTATION
# ==============================================================================
docs-serve: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build

openapi-export: ## Export OpenAPI schema to file
	$(COMPOSE_DEV) exec backend python -m scripts.export_openapi

# ==============================================================================
# BACKUP
# ==============================================================================
backup-db: ## Create database backup
	@mkdir -p backups
	$(COMPOSE_DEV) exec db pg_dump -U $${POSTGRES_USER} $${POSTGRES_DB} | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)✓ Backup created$(NC)"
