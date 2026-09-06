"""
Pytest global fixtures for backend tests.
"""

import os
import re
from collections.abc import AsyncGenerator

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.application.services.auth_security_service import AuthenticationSecurityRecorder
from src.domain.base import Base
from src.infrastructure.db.session import get_db_session
from src.main import app
from src.presentation.api.v1.auth.router import get_authentication_security_recorder

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
SAFE_TEST_DATABASE_NAME = re.compile(r"^[a-zA-Z0-9_]+_test$")


async def _recreate_test_database(database_url: str) -> None:
    """Recreate only an explicitly named PostgreSQL test database."""
    url = make_url(database_url)
    database_name = url.database or ""
    if not SAFE_TEST_DATABASE_NAME.fullmatch(database_name):
        pytest.fail("TEST_DATABASE_URL must target a database whose name ends with '_test'")
    if not url.drivername.startswith("postgresql"):
        pytest.fail("Integration tests require PostgreSQL")

    connection = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database="postgres",
    )
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await connection.close()


async def _drop_test_database(database_url: str) -> None:
    """Drop the validated test database after the integration session."""
    url = make_url(database_url)
    database_name = url.database or ""
    if not SAFE_TEST_DATABASE_NAME.fullmatch(database_name):
        pytest.fail("Refusing to drop a database without the '_test' suffix")
    connection = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database="postgres",
    )
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)')
    finally:
        await connection.close()


@pytest.fixture(scope="session")
async def test_engine():
    if not TEST_DATABASE_URL:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")

    await _recreate_test_database(TEST_DATABASE_URL)
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()
        await _drop_test_database(TEST_DATABASE_URL)


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if table_names:
        async with test_engine.begin() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))


@pytest.fixture
async def async_client(
    test_engine,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    security_session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    def override_security_recorder() -> AuthenticationSecurityRecorder:
        return AuthenticationSecurityRecorder(security_session_factory)

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_authentication_security_recorder] = override_security_recorder
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        yield client
    app.dependency_overrides.clear()
