"""
Encyklopedia Świętych Kościoła Katolickiego – Backend
Application Settings (Pydantic Settings v2)
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, EmailStr, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==============================================================================
# ENUMS
# ==============================================================================


class Environment(StrEnum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class AIProvider(StrEnum):
    """AI/embedding provider."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    NONE = "none"


class StorageBackend(StrEnum):
    """Object storage backend."""

    MINIO = "minio"
    S3 = "s3"
    LOCAL = "local"


# ==============================================================================
# SETTINGS
# ==============================================================================


class Settings(BaseSettings):
    """
    Central application configuration loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    Use ``get_settings()`` to get a cached instance.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "Encyklopedia Świętych Kościoła Katolickiego"
    APP_ENV: Environment = Environment.DEVELOPMENT
    APP_VERSION: str = "1.0.0"
    APP_SECRET_KEY: str
    APP_DEBUG: bool = False
    APP_LOG_LEVEL: str = "INFO"
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # ── Backend Server ─────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 4
    BACKEND_RELOAD: bool = False

    # ── CORS ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Database ───────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "all_saints"
    POSTGRES_USER: str = "saints_user"
    POSTGRES_PASSWORD: str

    DATABASE_URL: str | None = None
    DATABASE_URL_SYNC: str | None = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    @model_validator(mode="after")
    def assemble_db_urls(self) -> "Settings":
        """Build database URLs from components if not provided explicitly."""
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    CACHE_TTL_DEFAULT: int = 300       # 5 minutes
    CACHE_TTL_PERSONS: int = 600       # 10 minutes
    CACHE_TTL_STATIC: int = 3600       # 1 hour

    # ── Celery ─────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── JWT Authentication ─────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Security ───────────────────────────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    SECURE_COOKIES: bool = False
    CSRF_TRUSTED_ORIGINS: list[str] = []

    @field_validator("ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS", mode="before")
    @classmethod
    def assemble_string_list(cls, v: str | list[str]) -> list[str]:
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    # ── Rate Limiting ──────────────────────────────────────────────────────────
    RATE_LIMIT_PUBLIC: str = "100/minute"
    RATE_LIMIT_AUTHENTICATED: str = "1000/minute"
    RATE_LIMIT_ADMIN: str = "5000/minute"

    # ── Storage ────────────────────────────────────────────────────────────────
    STORAGE_BACKEND: StorageBackend = StorageBackend.MINIO

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_IMAGES: str = "saints-images"
    MINIO_BUCKET_DOCUMENTS: str = "saints-documents"
    MINIO_BUCKET_EXPORTS: str = "saints-exports"
    MINIO_USE_SSL: bool = False

    # AWS S3 (production)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-central-1"
    AWS_S3_BUCKET: str = ""

    # ── Email ──────────────────────────────────────────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: EmailStr = "noreply@all-saints.local"
    SMTP_TLS: bool = False
    SMTP_SSL: bool = False

    # ── AI / Embeddings ────────────────────────────────────────────────────────
    AI_PROVIDER: AIProvider = AIProvider.NONE
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_COMPLETION_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSIONS: int = 1536

    # ── Initial Admin ──────────────────────────────────────────────────────────
    INITIAL_ADMIN_EMAIL: EmailStr = "admin@all-saints.local"
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_FULL_NAME: str = "System Administrator"

    # ── Monitoring ─────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = True

    # ── Features ───────────────────────────────────────────────────────────────
    FEATURE_AI_SEARCH: bool = False
    FEATURE_MAPS: bool = True
    FEATURE_TIMELINE: bool = True
    FEATURE_EXPORTS: bool = True

    # ── Computed Properties ────────────────────────────────────────────────────

    @property
    def is_development(self) -> bool:
        """True if running in development mode."""
        return self.APP_ENV == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """True if running in production mode."""
        return self.APP_ENV == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        """True if running in test mode."""
        return self.APP_ENV == Environment.TESTING

    @property
    def docs_url(self) -> str | None:
        """OpenAPI docs URL – disabled in production."""
        return "/docs" if not self.is_production else None

    @property
    def redoc_url(self) -> str | None:
        """ReDoc URL – disabled in production."""
        return "/redoc" if not self.is_production else None

    @property
    def openapi_url(self) -> str | None:
        """OpenAPI schema URL – disabled in production."""
        return "/openapi.json" if not self.is_production else None


@lru_cache
def get_settings() -> Settings:
    """
    Return cached Settings instance.

    Uses LRU cache to ensure settings are loaded only once.
    In tests, clear with ``get_settings.cache_clear()``.
    """
    return Settings()  # type: ignore[call-arg]


# Convenience alias used across the application
settings: Settings = get_settings()
