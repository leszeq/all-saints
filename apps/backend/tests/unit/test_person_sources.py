"""Contract checks for assigning editorial sources to persons."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.main import app
from src.presentation.api.v1.sources.schemas import (
    PersonSourceCreateSchema,
    PersonWebSourceCreateSchema,
)


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


def test_person_web_source_requires_http_url() -> None:
    source = PersonWebSourceCreateSchema(
        title="Oficjalny biogram",
        url="https://example.org/saint",
    )

    assert str(source.url) == "https://example.org/saint"
    with pytest.raises(ValidationError):
        PersonWebSourceCreateSchema(
            title="Nieprawidłowe źródło",
            url="ftp://example.org/saint",
        )


def test_person_source_management_is_exposed_as_protected_api() -> None:
    schema = app.openapi()
    list_operation = schema["paths"]["/api/v1/sources/person-links/{person_id}"]["get"]
    create_operation = schema["paths"]["/api/v1/sources/person-links/{person_id}"]["post"]
    create_web_operation = schema["paths"]["/api/v1/sources/person-links/{person_id}/web"]["post"]
    delete_operation = schema["paths"]["/api/v1/sources/person-links/{person_id}/{link_id}"][
        "delete"
    ]

    assert list_operation["security"] == [{"HTTPBearer": []}]
    assert create_operation["security"] == [{"HTTPBearer": []}]
    assert create_web_operation["security"] == [{"HTTPBearer": []}]
    assert delete_operation["security"] == [{"HTTPBearer": []}]


def test_source_statistics_are_public_and_quality_report_is_protected() -> None:
    schema = app.openapi()
    source_stats = schema["paths"]["/api/v1/sources/stats"]["get"]
    quality_report = schema["paths"]["/api/v1/editorial/quality"]["get"]

    assert "security" not in source_stats
    assert quality_report["security"] == [{"HTTPBearer": []}]


def test_source_catalogue_preserves_public_reads_and_protected_writes() -> None:
    paths = app.openapi()["paths"]

    for path in (
        "/api/v1/sources/bibliography",
        "/api/v1/sources/historical-sources",
    ):
        assert "security" not in paths[path]["get"]
        assert paths[path]["post"]["security"] == [{"HTTPBearer": []}]


def test_editorial_media_catalogues_require_authentication() -> None:
    schema = app.openapi()
    images = schema["paths"]["/api/v1/sources/images"]["get"]
    documents = schema["paths"]["/api/v1/sources/documents"]["get"]

    assert images["security"] == [{"HTTPBearer": []}]
    assert documents["security"] == [{"HTTPBearer": []}]
