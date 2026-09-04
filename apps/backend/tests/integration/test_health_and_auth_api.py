"""
Integration tests for Health and Auth API endpoints.
"""

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
