"""
Integration tests for Health and Auth API endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.identity.models import AuditAction, AuditLog


@pytest.mark.asyncio
async def test_health_liveness_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_info_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health/info")
    assert response.status_code == 200
    data = response.json()
    assert "features" in data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("db_ok", "redis_ok", "expected_status"),
    [
        (True, True, 200),
        (False, True, 503),
        (True, False, 503),
    ],
)
async def test_readiness_requires_database_and_redis(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    db_ok: bool,
    redis_ok: bool,
    expected_status: int,
):
    monkeypatch.setattr(
        "src.presentation.health.check_db_connection",
        AsyncMock(return_value=db_ok),
    )
    monkeypatch.setattr(
        "src.presentation.health.check_redis_connection",
        AsyncMock(return_value=redis_ok),
    )

    response = await async_client.get("/health/ready")

    assert response.status_code == expected_status
    data = response.json()
    assert data["status"] == ("ready" if expected_status == 200 else "unavailable")
    assert data["checks"] == {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }


@pytest.mark.asyncio
async def test_untrusted_host_is_rejected(async_client: AsyncClient):
    response = await async_client.get(
        "/health", headers={"Host": "attacker.example"}
    )

    assert response.status_code == 400
    assert response.text == "Invalid host header"


@pytest.mark.asyncio
async def test_login_invalid_credentials(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.org", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"] == "UNAUTHORIZED"
    assert data["message"] == "Nieprawidłowy email lub hasło"
    assert data["detail"] == "Nieprawidłowy email lub hasło"
    assert data["request_id"] == response.headers["x-request-id"]
    audit_log = (await db_session.execute(select(AuditLog))).scalar_one()
    assert audit_log.action == AuditAction.LOGIN_FAILED.value
    assert audit_log.resource_type == "authentication"
    assert audit_log.request_id == response.headers["x-request-id"]
