"""Regression tests for creating person records from the admin form."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.person_service import (
    ERA_PERIOD_ERAS,
    PATRONAGE_GROUP_TYPES,
    PersonService,
)
from src.domain.hagiography.models import (
    Era,
    EraPeriod,
    Gender,
    PatronageGroup,
    Person,
    PersonType,
    PersonVersion,
)
from src.main import app
from src.presentation.api.v1.persons.schemas import (
    PersonCreateSchema,
    PersonDetailSchema,
    PersonListItemSchema,
    PersonUpdateSchema,
)

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


def test_person_content_fields_and_state_of_life_are_exposed_in_detail() -> None:
    person_id = uuid.uuid4()
    state_id = uuid.uuid4()
    now = "2026-08-23T12:00:00Z"

    payload = PersonDetailSchema.model_validate(
        {
            "id": person_id,
            "slug": "sw-rita-z-cascii",
            "canonical_name": "Św. Rita z Cascii",
            "person_type": "saint",
            "status": "draft",
            "gender": "female",
            "era": "medieval",
            "is_featured": True,
            "prayers": "Święta Rito, módl się za nami.",
            "iconographic_attributes": "Róże; cierń na czole",
            "state_of_life_id": state_id,
            "state_of_life": {
                "id": state_id,
                "name_pl": "Zakonnica",
                "name_en": "Religious sister",
            },
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
    )

    assert payload.prayers == "Święta Rito, módl się za nami."
    assert payload.iconographic_attributes == "Róże; cierń na czole"
    assert payload.state_of_life is not None
    assert payload.state_of_life.name_pl == "Zakonnica"


def test_latin_name_is_exposed_in_person_lists() -> None:
    now = "2026-08-26T12:00:00Z"
    payload = PersonListItemSchema.model_validate(
        {
            "id": uuid.uuid4(),
            "slug": "sw-jan-pawel-ii",
            "canonical_name": "Św. Jan Paweł II",
            "latin_name": "Sanctus Ioannes Paulus II",
            "person_type": "saint",
            "status": "published",
            "gender": "male",
            "is_featured": False,
            "created_at": now,
            "updated_at": now,
        }
    )

    assert payload.latin_name == "Sanctus Ioannes Paulus II"


def test_patronages_and_iconographic_attributes_are_exposed_in_person_lists() -> None:
    now = "2026-08-28T12:00:00Z"
    payload = PersonListItemSchema.model_validate(
        {
            "id": uuid.uuid4(),
            "slug": "sw-rita-z-cascii",
            "canonical_name": "Św. Rita z Cascii",
            "latin_name": "Sancta Rita de Cassia",
            "person_type": "saint",
            "status": "published",
            "gender": "female",
            "iconographic_attributes": "róże; cierń na czole",
            "patronages": [
                {
                    "id": uuid.uuid4(),
                    "patronage_type": "family",
                    "name_pl": "Małżeństwa",
                    "is_official": True,
                },
                {
                    "id": uuid.uuid4(),
                    "patronage_type": "illness",
                    "name_pl": "Sprawy beznadziejne",
                    "is_official": False,
                },
            ],
            "is_featured": False,
            "created_at": now,
            "updated_at": now,
        }
    )

    assert payload.iconographic_attributes == "róże; cierń na czole"
    assert [patronage.name_pl for patronage in payload.patronages] == [
        "Małżeństwa",
        "Sprawy beznadziejne",
    ]


def test_person_recognition_dates_are_editable_and_exposed_in_detail() -> None:
    create_payload = PersonCreateSchema.model_validate(
        {
            **ADMIN_PAYLOAD,
            "beatification": {
                "beatification_date": "2011-05-01",
                "beatification_year": 2011,
            },
            "canonization": {
                "canonization_date": "2014-04-27",
                "canonization_year": 2014,
            },
        }
    )
    now = "2026-08-25T12:00:00Z"
    detail = PersonDetailSchema.model_validate(
        {
            "id": uuid.uuid4(),
            "slug": "sw-jan-pawel-ii",
            "canonical_name": "Św. Jan Paweł II",
            "person_type": "saint",
            "status": "published",
            "gender": "male",
            "is_featured": True,
            "beatification": {
                "id": uuid.uuid4(),
                **create_payload.beatification.model_dump(),
            },
            "canonization": {
                "id": uuid.uuid4(),
                **create_payload.canonization.model_dump(),
            },
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
    )

    assert detail.beatification is not None
    assert detail.beatification.beatification_date == "2011-05-01"
    assert detail.canonization is not None
    assert detail.canonization.canonization_date == "2014-04-27"


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

    person = await service.create_person(
        PersonCreateSchema.model_validate(
            {**ADMIN_PAYLOAD, "latin_name": "Sanctus Ioannes Paulus II"}
        ),
        user_id,
    )

    assert person.slug == "sw-jan-pawel-ii"
    assert person.latin_name == "Sanctus Ioannes Paulus II"
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


def test_timeline_periods_cover_the_expected_eras() -> None:
    schema = app.openapi()

    assert ERA_PERIOD_ERAS[EraPeriod.EARLY_WITNESSES] == (
        Era.APOSTOLIC,
        Era.EARLY_CHURCH,
        Era.LATE_ANTIQUITY,
    )
    assert ERA_PERIOD_ERAS[EraPeriod.MEDIEVAL] == (Era.MEDIEVAL,)
    assert ERA_PERIOD_ERAS[EraPeriod.RENEWAL] == (Era.EARLY_MODERN,)
    assert ERA_PERIOD_ERAS[EraPeriod.MODERN] == (Era.MODERN, Era.CONTEMPORARY)

    public_parameters = schema["paths"]["/api/v1/persons"]["get"]["parameters"]
    assert any(parameter["name"] == "period" for parameter in public_parameters)


def test_patronage_groups_are_structured_and_exposed_by_the_api() -> None:
    schema = app.openapi()
    person = PersonCreateSchema.model_validate(
        {
            **ADMIN_PAYLOAD,
            "patronages": [
                {
                    "patronage_type": "illness",
                    "name_pl": "Osoby chore",
                    "is_official": True,
                }
            ],
        }
    )

    assert person.patronages[0].name_pl == "Osoby chore"
    assert PATRONAGE_GROUP_TYPES[PatronageGroup.HEALTH] == ("illness", "healthcare")
    assert PATRONAGE_GROUP_TYPES[PatronageGroup.FAMILY] == ("family",)
    assert PATRONAGE_GROUP_TYPES[PatronageGroup.WORK] == ("profession", "work")
    assert PATRONAGE_GROUP_TYPES[PatronageGroup.TRAVEL] == ("travel",)

    public_parameters = schema["paths"]["/api/v1/persons"]["get"]["parameters"]
    assert any(parameter["name"] == "patronage" for parameter in public_parameters)


@pytest.mark.asyncio
async def test_person_service_accepts_public_multi_select_filters() -> None:
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    await PersonService(db).list_persons(
        person_type=[PersonType.SAINT, PersonType.BLESSED],
        gender=[Gender.MALE, Gender.FEMALE],
        period=[EraPeriod.MEDIEVAL, EraPeriod.MODERN],
        patronage=[PatronageGroup.HEALTH, PatronageGroup.FAMILY],
        published_only=True,
    )

    statement = db.execute.await_args_list[0].args[0]
    params = set()
    for value in statement.compile().params.values():
        if isinstance(value, list):
            params.update(value)
        else:
            params.add(value)

    assert {"saint", "blessed", "male", "female", "published"}.issubset(params)
    assert {"medieval", "modern", "contemporary"}.issubset(params)
    assert {"illness", "healthcare", "family"}.issubset(params)


@pytest.mark.asyncio
async def test_person_service_searches_patronages_and_iconographic_attributes() -> None:
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    await PersonService(db).list_persons(search="róża", published_only=True)

    statement = db.execute.await_args_list[0].args[0]
    compiled = str(statement)

    assert "iconographic_attributes" in compiled
    assert "patronages" in compiled
