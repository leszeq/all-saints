"""
Integration tests for Person API endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_persons_empty(async_client: AsyncClient):
    response = await async_client.get("/api/v1/persons")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_nonexistent_person(async_client: AsyncClient):
    response = await async_client.get("/api/v1/persons/nonexistent-slug")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Osoba nie została znaleziona"
