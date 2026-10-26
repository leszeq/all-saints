"""Contract checks for privacy-preserving product analytics ingestion."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.main import app
from src.presentation.api.v1.analytics.router import (
    ProductEventCreateSchema,
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
