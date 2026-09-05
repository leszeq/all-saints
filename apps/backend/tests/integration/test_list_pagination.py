"""Integration coverage for the shared list pagination contract."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.geography.models import Place
from src.domain.sources.models import Bibliography


def assert_page_headers(
    response: Response,
    *,
    total: int,
    page: int,
    per_page: int,
    total_pages: int,
) -> None:
    headers = response.headers
    assert headers["x-total-count"] == str(total)
    assert headers["x-page"] == str(page)
    assert headers["x-per-page"] == str(per_page)
    assert headers["x-total-pages"] == str(total_pages)


@pytest.mark.asyncio
async def test_geography_list_returns_requested_page_and_total(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    db_session.add_all([Place(name="Asyż"), Place(name="Cascia"), Place(name="Rzym")])
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/geography/places",
        params={"page": 2, "per_page": 1},
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Cascia"]
    assert_page_headers(response, total=3, page=2, per_page=1, total_pages=3)


@pytest.mark.asyncio
async def test_source_page_count_respects_active_search_filter(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            Bibliography(title="Acta Sanctorum — styczeń"),
            Bibliography(title="Acta Sanctorum — luty"),
            Bibliography(title="Martyrologium Romanum"),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/sources/bibliography",
        params={"search": "Acta Sanctorum", "page": 1, "per_page": 1},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert_page_headers(response, total=2, page=1, per_page=1, total_pages=2)


@pytest.mark.asyncio
async def test_page_size_is_bounded_by_the_public_contract(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(
        "/api/v1/taxonomy/tags",
        params={"page": 1, "per_page": 501},
    )

    assert response.status_code == 422
