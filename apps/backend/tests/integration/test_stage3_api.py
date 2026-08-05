"""
Integration tests for Stage 3 API endpoints (Geography, Orders, Popes, Sources, Taxonomy).
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_geography_countries_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/geography/countries")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_orders_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_popes_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/popes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_sources_bibliography_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/sources/bibliography")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_taxonomy_categories_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/taxonomy/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
