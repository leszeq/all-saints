"""Integration coverage for privacy-preserving product analytics ingestion."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.analytics.models import ProductEvent


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
