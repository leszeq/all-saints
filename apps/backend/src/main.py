"""
FastAPI application factory and middleware configuration.

Architecture:
- Clean startup/shutdown lifecycle management
- Structured request logging with correlation IDs
- CORS, GZip, security headers
- Prometheus metrics
- Global exception handlers
- OpenAPI documentation configuration
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.config import settings
from src.core.logging import setup_logging
from src.infrastructure.cache.redis_client import check_redis_connection, close_redis_pool
from src.infrastructure.db.session import check_db_connection, close_db_connections


# ==============================================================================
# LIFESPAN (startup / shutdown)
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Runs startup tasks before yielding control to FastAPI,
    then runs shutdown tasks when the application is stopping.
    """
    # ── Startup ────────────────────────────────────────────────────────────────
    setup_logging(
        log_level=settings.APP_LOG_LEVEL,
        json_logs=settings.is_production,
    )

    logger.info(
        "Starting {name} v{version} [{env}]",
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )

    # Verify database connectivity
    if not await check_db_connection():
        logger.critical("Cannot connect to PostgreSQL – aborting startup")
        raise RuntimeError("Database connection failed")
    logger.info("✓ PostgreSQL connected")

    # Verify Redis connectivity
    if not await check_redis_connection():
        logger.warning("Redis not available – caching disabled")
    else:
        logger.info("✓ Redis connected")

    logger.info("✓ Application startup complete")

    yield  # Application is running

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("Shutting down application...")
    await close_db_connections()
    await close_redis_pool()
    logger.info("✓ Application shutdown complete")


# ==============================================================================
# APPLICATION FACTORY
# ==============================================================================


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
## Encyklopedia Świętych Kościoła Katolickiego – API

Kompletny system zarządzania danymi hagiograficznymi.

### Funkcje:
- 📚 Zarządzanie świętymi, błogosławionymi i kandydatami na ołtarze
- 🔍 Wyszukiwanie pełnotekstowe i semantyczne
- 🗓️ Kalendarz liturgiczny
- 📍 Mapy sanktuariów i miejsc
- 📤 Eksport do Excel, PDF, DOCX, JSON, XML
- 🤖 Moduły AI (tagi, streszczenia, powiązania)

### Autoryzacja:
Bearer JWT token wymagany dla większości endpointów.
        """,
        version=settings.APP_VERSION,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        swagger_ui_parameters={
            "displayRequestDuration": True,
            "filter": True,
            "persistAuthorization": True,
            "tryItOutEnabled": True,
        },
        lifespan=lifespan,
        contact={
            "name": "All Saints Development Team",
            "email": "dev@encyklopedia.pl",
        },
        license_info={
            "name": "Proprietary",
        },
        openapi_tags=[
            {"name": "auth", "description": "Logowanie, tokeny JWT i konto bieżącego użytkownika"},
            {"name": "persons", "description": "Osoby, święci, wersjonowanie i workflow publikacyjny"},
            {"name": "geography", "description": "Kraje, miejsca, diecezje i kościoły"},
            {"name": "taxonomy", "description": "Kategorie, tagi, stany życia i zawody"},
            {"name": "orders", "description": "Zakony i zgromadzenia"},
            {"name": "popes", "description": "Papieże i dane o kanonizacjach"},
            {"name": "sources", "description": "Bibliografia, źródła historyczne, media i dokumenty"},
            {"name": "users", "description": "Użytkownicy i uprawnienia panelu administracyjnego"},
            {"name": "health", "description": "Stan aplikacji i jej zależności"},
        ],
    )

    # ── Middleware (order matters – outermost first) ────────────────────────────
    _setup_middleware(app)

    # Instrumentation must be registered before the Starlette lifespan starts.
    if settings.PROMETHEUS_ENABLED:
        Instrumentator().instrument(app).expose(app)

    # ── Exception handlers ─────────────────────────────────────────────────────
    _setup_exception_handlers(app)

    # ── Routers ────────────────────────────────────────────────────────────────
    _include_routers(app)

    return app


# ==============================================================================
# MIDDLEWARE
# ==============================================================================


def _setup_middleware(app: FastAPI) -> None:
    """Register all middleware in correct order."""

    # GZip compression (compress responses > 1KB)
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Authorization",
            "Content-Type",
            "X-Requested-With",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "X-Process-Time"],
        max_age=86400,  # 24 hours preflight cache
    )

    # Security headers + request ID + timing
    @app.middleware("http")
    async def security_and_logging_middleware(
        request: Request, call_next: Any
    ) -> Response:
        """
        Add security headers, request ID, and timing to every response.

        Also logs all incoming requests with correlation ID.
        """
        # Generate correlation ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger.info(
            "{method} {path}",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
            client=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        process_time = (time.perf_counter() - start_time) * 1000

        # Security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com"
            )

        logger.info(
            "{method} {path} → {status} ({time:.0f}ms)",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            time=process_time,
            request_id=request_id,
        )

        return response


# ==============================================================================
# EXCEPTION HANDLERS
# ==============================================================================


def _setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError
    from sqlalchemy.exc import IntegrityError

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return structured validation errors."""
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Dane wejściowe zawierają błędy walidacji",
                "details": errors,
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """Handle database integrity constraint violations."""
        logger.warning(f"Database integrity error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "CONFLICT",
                "message": "Naruszenie unikalności danych – rekord już istnieje",
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions."""
        logger.exception(f"Unhandled exception on {request.method} {request.url}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "Wystąpił nieoczekiwany błąd serwera",
            },
        )


# ==============================================================================
# ROUTERS
# ==============================================================================


def _include_routers(app: FastAPI) -> None:
    """Register all API routers."""
    from src.presentation.api.v1 import router as api_v1_router
    from src.presentation.health import router as health_router

    # Health check (no auth required)
    app.include_router(health_router)

    # API v1
    app.include_router(api_v1_router, prefix="/api/v1")


# ==============================================================================
# ENTRY POINT
# ==============================================================================


app = create_app()


# Fix type hint in middleware
from typing import Any  # noqa: E402
