# ==============================================================================
# Backend Dockerfile
# Multi-stage build: development + production
# ==============================================================================

# ── Base ──────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

LABEL maintainer="All Saints Team <dev@all-saints.local>"
LABEL org.opencontainers.image.title="All Saints Backend"
LABEL org.opencontainers.image.description="Encyklopedia Świętych – FastAPI Backend"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    VENV_PATH="/app/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    # WeasyPrint dependencies
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS dependencies

COPY pyproject.toml ./
RUN poetry install --only=main --no-root

# ── Development ───────────────────────────────────────────────────────────────
FROM base AS development

COPY pyproject.toml ./
RUN poetry install --no-root

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# ── Builder ───────────────────────────────────────────────────────────────────
FROM dependencies AS builder

COPY . .
RUN poetry build

# ── Production ────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    VENV_PATH="/app/.venv"

ENV PATH="$VENV_PATH/bin:$PATH"

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /bin/bash appuser

# System runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    libwebp7 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from dependencies stage
COPY --from=dependencies /app/.venv .venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "src.main:app", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--workers", "4", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "120", \
    "--keepalive", "5", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
