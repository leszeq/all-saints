"""Public patronage concept directory tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import Gender, Patronage, Person, PersonType, PublicationStatus


@pytest.mark.asyncio
async def test_public_patronage_concepts_keep_type_and_public_visibility_boundaries(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    doctor_one = Person(
        slug="sw-patron-lekarz-1",
        canonical_name="Św. Lekarz Pierwszy",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
    )
    doctor_two = Person(
        slug="sw-patron-lekarz-2",
        canonical_name="Św. Lekarz Drugi",
        person_type=PersonType.BLESSED.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.FEMALE.value,
    )
    draft = Person(
        slug="draft-patron-lekarz",
        canonical_name="Roboczy Lekarz",
        person_type=PersonType.CANDIDATE.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.MALE.value,
    )
    db_session.add_all([doctor_one, doctor_two, draft])
    await db_session.flush()
    db_session.add_all(
        [
            Patronage(
                person_id=doctor_one.id,
                patronage_type="profession",
                name_pl="Lekarzy",
                name_en="Doctors",
                is_official=True,
            ),
            Patronage(
                person_id=doctor_two.id,
                patronage_type="profession",
                name_pl="Lekarzy",
                name_en="Doctors",
            ),
            Patronage(
                person_id=draft.id,
                patronage_type="profession",
                name_pl="Lekarzy",
                name_en="Doctors",
            ),
            Patronage(
                person_id=doctor_one.id,
                patronage_type="city",
                name_pl="Lekarzy",
                name_en="Doctors",
            ),
        ]
    )
    await db_session.commit()

    concepts = await async_client.get("/api/v1/taxonomy/patronages")
    assert concepts.status_code == 200
    assert concepts.headers["x-total-count"] == "2"
    assert concepts.json() == [
        {
            "slug": "city-lekarzy",
            "patronage_type": "city",
            "name_pl": "Lekarzy",
            "name_en": "Doctors",
            "description": None,
            "person_count": 1,
        },
        {
            "slug": "profession-lekarzy",
            "patronage_type": "profession",
            "name_pl": "Lekarzy",
            "name_en": "Doctors",
            "description": None,
            "person_count": 2,
        },
    ]

    persons = await async_client.get(
        "/api/v1/taxonomy/patronages/profession-lekarzy/persons"
    )
    assert persons.status_code == 200
    assert persons.json()["concept"]["slug"] == "profession-lekarzy"
    assert persons.json()["total"] == 2
    assert [item["slug"] for item in persons.json()["items"]] == [
        "sw-patron-lekarz-2",
        "sw-patron-lekarz-1",
    ]

    missing = await async_client.get("/api/v1/taxonomy/patronages/unknown/persons")
    assert missing.status_code == 404
