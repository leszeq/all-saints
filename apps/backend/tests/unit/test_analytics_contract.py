"""Contract checks for privacy-preserving product analytics ingestion."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.domain.analytics.models import ProductEvent
from src.main import app
from src.presentation.api.v1.analytics.router import (
    ProductEventCreateSchema,
    _aggregate_events,
    hash_session_id,
)


def test_product_event_route_is_public_and_stable() -> None:
    assert str(app.url_path_for("record_product_event")) == "/api/v1/events"
    operation = app.openapi()["paths"]["/api/v1/events"]["post"]
    assert "security" not in operation


def test_product_event_contract_rejects_raw_query_and_arbitrary_properties() -> None:
    session_id = str(uuid.uuid4())
    valid = {
        "event_name": "search_results",
        "session_id": session_id,
        "query_class": "name",
        "properties": {"result_count": 0},
    }

    payload = ProductEventCreateSchema.model_validate(valid)
    assert payload.properties.result_count == 0

    with pytest.raises(ValidationError):
        ProductEventCreateSchema.model_validate({**valid, "query": "Franciszek"})
    with pytest.raises(ValidationError):
        ProductEventCreateSchema.model_validate(
            {**valid, "properties": {"result_count": 0, "query": "Franciszek"}}
        )


def test_session_identifier_is_hashed_with_a_stable_secret_bound_digest() -> None:
    session_id = uuid.uuid4()

    digest = hash_session_id(session_id)

    assert len(digest) == 64
    assert digest != str(session_id)
    assert digest == hash_session_id(session_id)


def test_daily_aggregation_counts_non_empty_and_zero_search_results() -> None:
    created_at = datetime(2026, 10, 26, 12, tzinfo=UTC)
    events = [
        ProductEvent(
            created_at=created_at,
            event_name="search_submitted",
            query_class="name",
            session_id_hash="session-a",
            properties={},
        ),
        ProductEvent(
            created_at=created_at,
            event_name="search_results",
            query_class="name",
            session_id_hash="session-a",
            properties={"result_count": 0},
        ),
        ProductEvent(
            created_at=created_at,
            event_name="search_results",
            query_class="name",
            session_id_hash="session-b",
            properties={"result_count": 3},
        ),
    ]

    rows = _aggregate_events(events)

    results = next(row for row in rows if row.event_name == "search_results")
    assert results.event_count == 2
    assert len(results.sessions) == 2
    assert results.result_count_sum == 3
    assert results.zero_results_count == 1
    assert results.search_success_count == 1
