"""Regression tests for creating person records from the admin form."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Person, PersonVersion
from src.main import app
from src.presentation.api.v1.persons.schemas import PersonCreateSchema, PersonUpdateSchema


ADMIN_PAYLOAD = {
    "canonical_name": "Św. Jan Paweł II",
    "canonical_name_en": "St. John Paul II",
    "latin_name": "",
    "person_type": "saint",
    "status": "draft",
    "gender": "male",
    "era": "contemporary",
    "birth_year": 1920,
    "death_year": 2005,
    "birth_country_id": "",
    "death_country_id": "",
    "state_of_life_id": "",
    "summary_pl": "Test",
    "biography_pl": "Test",
    "is_featured": False,
}


def test_person_create_schema_accepts_empty_optional_selects() -> None:
    payload = PersonCreateSchema.model_validate(ADMIN_PAYLOAD)

    assert payload.birth_country_id is None
    assert payload.death_country_id is None
    assert payload.state_of_life_id is None


def test_person_update_schema_accepts_empty_optional_selects() -> None:
    payload = PersonUpdateSchema.model_validate(
        {"birth_country_id": "", "death_country_id": " ", "state_of_life_id": ""}
    )

    assert payload.birth_country_id is None
    assert payload.death_country_id is None
    assert payload.state_of_life_id is None


@pytest.mark.asyncio
async def test_person_service_creates_json_safe_initial_snapshot() -> None:
    stored: list[object] = []
    db = MagicMock()

    def add(model: object) -> None:
        if isinstance(model, Person) and model.id is None:
            model.id = uuid.uuid4()
        stored.append(model)

    db.add.side_effect = add
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    service = PersonService(db)
    service._generate_unique_slug = AsyncMock(return_value="sw-jan-pawel-ii")
    user_id = uuid.uuid4()

    person = await service.create_person(PersonCreateSchema.model_validate(ADMIN_PAYLOAD), user_id)

    assert person.slug == "sw-jan-pawel-ii"
    snapshot = next(model for model in stored if isinstance(model, PersonVersion))
    assert snapshot.changed_by_id == user_id
    assert snapshot.snapshot["id"] == str(person.id)
    assert snapshot.snapshot["birth_country_id"] is None


def test_openapi_contains_all_active_modules_and_bearer_auth() -> None:
    schema = app.openapi()

    assert "/api/v1/persons" in schema["paths"]
    assert "/api/v1/geography/countries" in schema["paths"]
    assert "/api/v1/taxonomy/states-of-life" in schema["paths"]
    assert "/api/v1/orders" in schema["paths"]
    assert "/api/v1/popes" in schema["paths"]
    assert "/api/v1/sources/bibliography" in schema["paths"]
    assert "/api/v1/users" in schema["paths"]
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
