"""Protected, non-sensitive application settings endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.core.config import settings
from src.domain.identity.models import User
from src.presentation.api.v1.auth.router import get_current_user

router = APIRouter()


class FeatureFlagsSchema(BaseModel):
    """Feature switches exposed to the admin UI."""

    ai_search: bool
    maps: bool
    timeline: bool
    exports: bool


class AISettingsSchema(BaseModel):
    """Safe AI provider configuration without secrets."""

    provider: str
    openai_configured: bool
    embedding_model: str
    completion_model: str
    ollama_base_url: str | None
    ollama_embedding_model: str
    ollama_llm_model: str
    embedding_dimensions: int


class StorageSettingsSchema(BaseModel):
    """Safe storage configuration without credentials."""

    backend: str
    images_bucket: str
    documents_bucket: str
    exports_bucket: str
    public_endpoint: str | None


class SecuritySettingsSchema(BaseModel):
    """Safe authentication/session settings."""

    access_token_minutes: int
    refresh_token_days: int
    secure_cookies: bool
    cors_origins: list[str]
    docs_enabled: bool


class ApplicationSettingsResponse(BaseModel):
    """Complete read-only settings payload for the admin panel."""

    app_name: str
    app_version: str
    environment: str
    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None
    features: FeatureFlagsSchema
    ai: AISettingsSchema
    storage: StorageSettingsSchema
    security: SecuritySettingsSchema


@router.get(
    "",
    response_model=ApplicationSettingsResponse,
    summary="Read application settings",
    description="Return non-sensitive system configuration for the admin settings screen.",
)
async def get_application_settings(
    _user: User = Depends(get_current_user),
) -> ApplicationSettingsResponse:
    """Return safe, non-secret application configuration."""
    public_endpoint = None
    if settings.STORAGE_BACKEND.value == "minio":
        protocol = "https" if settings.MINIO_USE_SSL else "http"
        public_endpoint = f"{protocol}://{settings.MINIO_ENDPOINT}"

    return ApplicationSettingsResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.APP_ENV.value,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        features=FeatureFlagsSchema(
            ai_search=settings.FEATURE_AI_SEARCH,
            maps=settings.FEATURE_MAPS,
            timeline=settings.FEATURE_TIMELINE,
            exports=settings.FEATURE_EXPORTS,
        ),
        ai=AISettingsSchema(
            provider=settings.AI_PROVIDER.value,
            openai_configured=bool(settings.OPENAI_API_KEY),
            embedding_model=settings.OPENAI_EMBEDDING_MODEL,
            completion_model=settings.OPENAI_COMPLETION_MODEL,
            ollama_base_url=(
                settings.OLLAMA_BASE_URL if settings.AI_PROVIDER.value == "ollama" else None
            ),
            ollama_embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
            ollama_llm_model=settings.OLLAMA_LLM_MODEL,
            embedding_dimensions=settings.EMBEDDING_DIMENSIONS,
        ),
        storage=StorageSettingsSchema(
            backend=settings.STORAGE_BACKEND.value,
            images_bucket=settings.MINIO_BUCKET_IMAGES,
            documents_bucket=settings.MINIO_BUCKET_DOCUMENTS,
            exports_bucket=settings.MINIO_BUCKET_EXPORTS,
            public_endpoint=public_endpoint,
        ),
        security=SecuritySettingsSchema(
            access_token_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_token_days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS,
            secure_cookies=settings.SECURE_COOKIES,
            cors_origins=settings.CORS_ORIGINS,
            docs_enabled=settings.docs_url is not None,
        ),
    )
