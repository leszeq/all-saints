"""
Integration tests for Health and Auth API endpoints.
"""

import pytest
from httpx import AsyncClient


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
async def test_login_invalid_credentials(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@all-saints.local", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Nieprawidłowy email lub hasło"
