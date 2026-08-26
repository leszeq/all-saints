"""Contract checks for assigning editorial sources to persons."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.main import app
from src.presentation.api.v1.sources.schemas import PersonSourceCreateSchema


def test_person_source_requires_exactly_one_source_kind() -> None:
    bibliography_id = uuid.uuid4()
    historical_source_id = uuid.uuid4()

    bibliography = PersonSourceCreateSchema(bibliography_id=bibliography_id)

    assert bibliography.bibliography_id == bibliography_id
    with pytest.raises(ValidationError, match="dokładnie jedno"):
        PersonSourceCreateSchema()
    with pytest.raises(ValidationError, match="dokładnie jedno"):
        PersonSourceCreateSchema(
            bibliography_id=bibliography_id,
            historical_source_id=historical_source_id,
        )


def test_person_source_management_is_exposed_as_protected_api() -> None:
    schema = app.openapi()
    list_operation = schema["paths"]["/api/v1/sources/person-links/{person_id}"]["get"]
    create_operation = schema["paths"]["/api/v1/sources/person-links/{person_id}"]["post"]
    delete_operation = schema["paths"][
        "/api/v1/sources/person-links/{person_id}/{link_id}"
    ]["delete"]

    assert list_operation["security"] == [{"HTTPBearer": []}]
    assert create_operation["security"] == [{"HTTPBearer": []}]
    assert delete_operation["security"] == [{"HTTPBearer": []}]
