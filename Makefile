.PHONY: help install setup dev dev-build dev-backend dev-db dev-detach stop \
	prod-check prod-build prod-up prod-down migrate migrate-create migrate-down migrate-history \
	seed reset-db test test-unit test-integration test-e2e test-coverage search-benchmark lint \
	lint-backend lint-frontend format format-check type-check type-check-backend \
	type-check-frontend audit logs logs-backend logs-db ps shell-backend shell-db clean \
	build export-xlsx export-pdf openapi-export backup-db translations-backfill-check \
	translations-backfill \
	prod-backup prod-restore-check

# ==============================================================================
# CONFIGURATION
# ==============================================================================
COMPOSE_DEV=docker compose -f infrastructure/docker/docker-compose.yml
BACKEND_RUN=$(COMPOSE_DEV) run --rm -T backend
PROD_ENV?=infrastructure/docker/.env.production
PROD_PROJECT?=all-saints-prod
COMPOSE_PROD=docker compose -p $(PROD_PROJECT) --env-file $(PROD_ENV) -f infrastructure/docker/docker-compose.prod.yml
BACKUP_DIR?=backups
BACKUP_FILE?=$(BACKUP_DIR)/all-saints-$(shell date -u +%Y%m%dT%H%M%SZ).dump
RESTORE_DB?=all_saints_restore_test_$(shell date -u +%Y%m%d%H%M%S)
E2E_PASSWORD?=DemoE2E123!

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
	@echo "$(CYAN)Building the backend development image...$(NC)"
	$(COMPOSE_DEV) build backend
	@echo "$(CYAN)Installing admin dependencies...$(NC)"
	cd apps/admin && npm ci
	@echo "$(CYAN)Installing web dependencies...$(NC)"
	cd apps/web && npm ci
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
prod-check: ## Validate production environment and Compose config
	@if [ ! -f "$(PROD_ENV)" ]; then echo "$(RED)Missing $(PROD_ENV). Copy infrastructure/docker/.env.production.example first.$(NC)"; exit 1; fi
	$(COMPOSE_PROD) config --quiet

prod-build: prod-check ## Build production images
	$(COMPOSE_PROD) build

prod-up: prod-check ## Start production stack
	$(COMPOSE_PROD) up -d --build --wait

prod-down: prod-check ## Stop production stack
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

translations-backfill-check: ## Preview legacy PL/EN translation backfill without writes
	$(COMPOSE_DEV) exec -T backend python -m src.infrastructure.db.backfill_person_translations

translations-backfill: ## Apply unambiguous legacy PL/EN translation backfill
	$(COMPOSE_DEV) exec -T backend python -m src.infrastructure.db.backfill_person_translations --apply

reset-db: ## ⚠ Drop and recreate the database (DESTRUCTIVE!)
	@echo "$(RED)⚠ This will DESTROY all data! Press Ctrl+C to abort...$(NC)"
	@sleep 5
	$(COMPOSE_DEV) exec -T db sh -c 'psql -U "$$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $$POSTGRES_DB;"'
	$(COMPOSE_DEV) exec -T db sh -c 'psql -U "$$POSTGRES_USER" -c "CREATE DATABASE $$POSTGRES_DB;"'
	$(MAKE) migrate
	$(MAKE) seed

# ==============================================================================
# TESTING
# ==============================================================================
test: ## Run all backend tests
	$(BACKEND_RUN) python -m pytest

test-unit: ## Run unit tests only
	$(BACKEND_RUN) python -m pytest -q -o addopts='' tests/unit

test-integration: ## Run integration tests only
	$(BACKEND_RUN) python -m pytest -q -o addopts='' tests/integration

search-benchmark: ## Evaluate the offline person-search benchmark (SEARCH_RESULTS=...)
	@test -n "$(SEARCH_RESULTS)" || (echo "Set SEARCH_RESULTS to a JSON result file under apps/backend" >&2; exit 2)
	$(BACKEND_RUN) python -m src.application.search_benchmark \
		--fixture data/search/search_gold_v1.json \
		--results "$(SEARCH_RESULTS)" \
		--check

test-e2e: ## Run Playwright smoke tests against the local development stack
	$(COMPOSE_DEV) up -d --wait db redis minio backend
	$(COMPOSE_DEV) exec -T backend alembic upgrade head
	@$(COMPOSE_DEV) run --rm -T -e SEED_DEMO_USERS=true -e DEMO_USER_PASSWORD="$(E2E_PASSWORD)" backend python -m src.infrastructure.db.seed
	cd apps/admin && npx playwright install chromium
	@cd apps/admin && E2E_PASSWORD="$(E2E_PASSWORD)" npm run test:e2e

test-coverage: ## Run tests with HTML coverage report
	$(BACKEND_RUN) python -m pytest --cov-report=html:htmlcov

# ==============================================================================
# CODE QUALITY
# ==============================================================================
lint: ## Run linters (Ruff + ESLint)
	$(MAKE) lint-backend
	$(MAKE) lint-frontend

lint-backend: ## Run Ruff for backend source and tests
	@echo "$(CYAN)Running Python linters...$(NC)"
	$(BACKEND_RUN) .venv/bin/ruff check src tests

format-check: ## Check backend formatting without modifying files
	$(BACKEND_RUN) .venv/bin/black --check src tests

lint-frontend: ## Run ESLint for admin and public portal
	@echo "$(CYAN)Running TypeScript linters...$(NC)"
	cd apps/admin && npm run lint
	cd apps/web && npm run lint

format: ## Auto-format backend code
	@echo "$(CYAN)Formatting Python code...$(NC)"
	$(BACKEND_RUN) .venv/bin/black src tests
	$(BACKEND_RUN) .venv/bin/ruff check --fix src tests

type-check: ## Run backend and frontend type checking
	$(MAKE) type-check-backend
	$(MAKE) type-check-frontend

type-check-backend: ## Run strict mypy for backend source
	$(BACKEND_RUN) .venv/bin/mypy src

type-check-frontend: ## Run TypeScript type checking
	cd apps/admin && npm run type-check
	cd apps/web && npm run type-check

audit: ## Audit locked backend and frontend dependencies
	$(BACKEND_RUN) .venv/bin/pip-audit
	cd apps/admin && npm run audit
	cd apps/web && npm run audit

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
	$(COMPOSE_DEV) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

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
	@echo "$(YELLOW)XLSX export is planned for Etap 7 and is not implemented yet.$(NC)"
	@false

export-pdf: ## Trigger Encyclopedia PDF export
	@echo "$(YELLOW)PDF export is planned for Etap 7 and is not implemented yet.$(NC)"
	@false

# ==============================================================================
# API DOCUMENTATION
# ==============================================================================
openapi-export: ## Export the current OpenAPI schema to apps/backend/openapi.json
	$(COMPOSE_DEV) exec -T backend python -c 'import json; from pathlib import Path; from src.main import app; Path("openapi.json").write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")'
	@echo "$(GREEN)✓ OpenAPI exported to apps/backend/openapi.json$(NC)"

# ==============================================================================
# BACKUP
# ==============================================================================
backup-db: ## Create database backup
	infrastructure/scripts/postgres-backup.sh "$(BACKUP_FILE)" $(COMPOSE_DEV)

prod-backup: prod-check ## Create an atomic production PostgreSQL backup
	infrastructure/scripts/postgres-backup.sh "$(BACKUP_FILE)" $(COMPOSE_PROD)

prod-restore-check: prod-check ## Restore a backup into an isolated temporary database
	infrastructure/scripts/postgres-restore-check.sh "$(BACKUP_FILE)" "$(RESTORE_DB)" $(COMPOSE_PROD)
