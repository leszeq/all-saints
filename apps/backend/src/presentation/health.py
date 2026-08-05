"""
Health check endpoints.

Provides liveness and readiness probes for Docker/Kubernetes.
No authentication required.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.infrastructure.cache.redis_client import check_redis_connection
from src.infrastructure.db.session import check_db_connection

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns 200 if the application process is running.",
    responses={200: {"description": "Application is alive"}},
)
async def health_liveness() -> dict:
    """
    Liveness probe.

    Returns basic application status without checking external dependencies.
    Used by Docker HEALTHCHECK and Kubernetes liveness probe.
    """
    return {
        "status": "alive",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Returns 200 if all critical dependencies are healthy.",
    responses={
        200: {"description": "All dependencies healthy"},
        503: {"description": "One or more dependencies unavailable"},
    },
)
async def health_readiness() -> JSONResponse:
    """
    Readiness probe.

    Checks all critical dependencies (database, Redis).
    Returns 503 if any dependency is unavailable.
    Used by load balancers to route traffic away from unhealthy instances.
    """
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    all_healthy = db_ok and redis_ok
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if all_healthy else "unavailable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        },
    )


@router.get(
    "/health/info",
    summary="Application info",
    description="Returns detailed application information (non-sensitive).",
)
async def health_info() -> dict:
    """Return non-sensitive application metadata."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "features": {
            "ai_search": settings.FEATURE_AI_SEARCH,
            "maps": settings.FEATURE_MAPS,
            "timeline": settings.FEATURE_TIMELINE,
            "exports": settings.FEATURE_EXPORTS,
        },
    }
