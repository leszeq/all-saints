"""Contract tests for religious order route composition."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


def test_order_routes_preserve_public_and_editorial_security_boundaries() -> None:
    paths = app.openapi()["paths"]

    assert "security" not in paths["/api/v1/orders"]["get"]
    assert "security" not in paths["/api/v1/orders/{id_or_slug}"]["get"]

    protected_operations = (
        paths["/api/v1/orders/management"]["get"],
        paths["/api/v1/orders/import/validate"]["post"],
        paths["/api/v1/orders/import"]["post"],
        paths["/api/v1/orders"]["post"],
        paths["/api/v1/orders/{id_or_slug}"]["patch"],
        paths["/api/v1/orders/{id_or_slug}"]["delete"],
        paths["/api/v1/orders/{id_or_slug}/members"]["post"],
        paths["/api/v1/orders/{id_or_slug}/members/{person_id}"]["delete"],
    )

    assert all(operation["security"] == [{"HTTPBearer": []}] for operation in protected_operations)


@pytest.mark.asyncio
async def test_order_management_route_precedes_public_slug_catchall() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        response = await client.get("/api/v1/orders/management")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_order_import_routes_precede_public_slug_catchall() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        response = await client.post(
            "/api/v1/orders/import/validate",
            json={"orders": [{"slug": "test-import", "name": "Test import"}]},
        )

    assert response.status_code == 401
