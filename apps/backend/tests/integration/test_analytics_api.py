"""Integration coverage for privacy-preserving product analytics ingestion."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.analytics.models import ProductEvent, ProductEventDailyAggregate
from src.presentation.api.v1.analytics.router import rebuild_product_event_aggregates


@pytest.mark.asyncio
async def test_product_event_is_stored_without_raw_session_or_query(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    session_id = str(uuid.uuid4())

    response = await async_client.post(
        "/api/v1/events",
        json={
            "event_name": "search_results",
            "session_id": session_id,
            "query_class": "name",
            "properties": {"result_count": 0},
        },
    )

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    event = (await db_session.execute(select(ProductEvent))).scalar_one()
    assert event.event_name == "search_results"
    assert event.query_class == "name"
    assert event.properties == {"result_count": 0}
    assert event.session_id_hash != session_id
    assert len(event.session_id_hash) == 64
    assert event.retention_until > event.created_at


@pytest.mark.asyncio
async def test_product_event_rejects_unknown_payload_fields(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/events",
        json={
            "event_name": "search_submitted",
            "session_id": str(uuid.uuid4()),
            "query": "Franciszek",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_aggregate_rebuild_exposes_only_daily_funnel_dimensions(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    created_at = datetime(2026, 10, 26, 12, tzinfo=UTC)
    db_session.add_all(
        [
            ProductEvent(
                created_at=created_at,
                event_name="search_results",
                query_class="name",
                session_id_hash="hashed-a",
                properties={"result_count": 0},
            ),
            ProductEvent(
                created_at=created_at,
                event_name="search_results",
                query_class="name",
                session_id_hash="hashed-b",
                properties={"result_count": 2},
            ),
            ProductEvent(
                created_at=created_at,
                event_name="profile_opened",
                query_class=None,
                session_id_hash="hashed-b",
                properties={},
            ),
        ]
    )
    await db_session.flush()

    response = await rebuild_product_event_aggregates(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 10, 26),
        db=db_session,
        _user=object(),  # type: ignore[arg-type]
    )
    await db_session.flush()

    assert response.start_date == date(2026, 10, 26)
    results = next(item for item in response.items if item.event_name.value == "search_results")
    assert results.event_count == 2
    assert results.zero_results_count == 1
    assert results.search_success_count == 1
    assert results.unique_sessions == 2
    assert results.result_count_sum == 2
    persisted = (await db_session.execute(select(ProductEventDailyAggregate))).scalars().all()
    assert len(persisted) == 2


@pytest.mark.asyncio
async def test_aggregate_read_requires_editorial_authentication(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/events/aggregates")

    assert response.status_code == 401
