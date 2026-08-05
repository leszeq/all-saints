"""
Database infrastructure – async SQLAlchemy session factory.

Provides:
- Async engine configured for PostgreSQL + pgvector
- Session factory with proper lifecycle management
- FastAPI dependency for database sessions
- Utility for running synchronous Alembic operations
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.config import settings


# ==============================================================================
# ENGINE
# ==============================================================================


def _create_engine(database_url: str, *, echo: bool = False, use_null_pool: bool = False) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine.

    Args:
        database_url: Async DSN (postgresql+asyncpg://...).
        echo: If True, log all SQL statements (development only).
        use_null_pool: If True, use NullPool (for testing/Alembic).

    Returns:
        Configured AsyncEngine instance.
    """
    engine_kwargs: dict[str, Any] = {
        "echo": echo,
        "echo_pool": False,
        "pool_pre_ping": True,
        "json_serializer": lambda obj: __import__("orjson").dumps(obj).decode(),
        "json_deserializer": lambda s: __import__("orjson").loads(s),
    }

    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs.update(
            {
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                "pool_recycle": 1800,  # Recycle connections every 30 minutes
            }
        )

    engine = create_async_engine(database_url, **engine_kwargs)

    # Log connection events (development only)
    if settings.is_development:

        @event.listens_for(engine.sync_engine, "connect")
        def on_connect(dbapi_connection: Any, connection_record: Any) -> None:
            logger.debug("Database connection established")

    return engine


# Singleton engine instances
_engine: AsyncEngine | None = None
_test_engine: AsyncEngine | None = None


def get_engine(*, for_testing: bool = False) -> AsyncEngine:
    """Return the singleton async engine."""
    global _engine, _test_engine

    if for_testing:
        if _test_engine is None:
            _test_engine = _create_engine(
                settings.DATABASE_URL,  # type: ignore[arg-type]
                echo=True,
                use_null_pool=True,
            )
        return _test_engine

    if _engine is None:
        _engine = _create_engine(
            settings.DATABASE_URL,  # type: ignore[arg-type]
            echo=settings.DATABASE_ECHO,
        )
    return _engine


# ==============================================================================
# SESSION FACTORY
# ==============================================================================


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to the given engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Singleton session factory
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


# ==============================================================================
# FASTAPI DEPENDENCY
# ==============================================================================


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db_session)):
            ...

    Automatically commits on success and rolls back on exception.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==============================================================================
# DATABASE LIFECYCLE
# ==============================================================================


async def check_db_connection() -> bool:
    """
    Verify that the database is reachable.

    Used for health checks and startup validation.

    Returns:
        True if connection succeeds, False otherwise.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False


async def close_db_connections() -> None:
    """Dispose of all database connections. Called on application shutdown."""
    global _engine, _test_engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connections closed")
    if _test_engine is not None:
        await _test_engine.dispose()


async def enable_pgvector(session: AsyncSession) -> None:
    """
    Enable the pgvector extension in the database.

    Must be called once during database initialisation.
    """
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    await session.commit()
    logger.info("PostgreSQL extensions enabled: vector, pg_trgm, unaccent")
