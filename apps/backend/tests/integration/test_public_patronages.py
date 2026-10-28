"""Public patronage concept directory tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import (
    ConceptAlias,
    ConceptAliasKind,
    ConceptAssignmentStatus,
    Gender,
    Patronage,
    PatronageConcept,
    PatronageConceptStatus,
    Person,
    PersonPatronageConcept,
    PersonType,
    PublicationStatus,
)


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

    persons = await async_client.get("/api/v1/taxonomy/patronages/profession-lekarzy/persons")
    assert persons.status_code == 200
    assert persons.json()["concept"]["slug"] == "profession-lekarzy"
    assert persons.json()["total"] == 2
    assert [item["slug"] for item in persons.json()["items"]] == [
        "sw-patron-lekarz-2",
        "sw-patron-lekarz-1",
    ]

    missing = await async_client.get("/api/v1/taxonomy/patronages/unknown/persons")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_public_patronages_prioritize_reviewed_concepts_and_alias_search(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    reviewed_person = Person(
        slug="sw-reviewed-patron",
        canonical_name="Święty Patron Zatwierdzony",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
    )
    legacy_person = Person(
        slug="sw-legacy-patron",
        canonical_name="Święty Patron Nieprzypisany",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
    )
    db_session.add_all([reviewed_person, legacy_person])
    await db_session.flush()

    reviewed_source = Patronage(
        person_id=reviewed_person.id,
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
    )
    legacy_source = Patronage(
        person_id=legacy_person.id,
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
    )
    concept = PatronageConcept(
        slug="profession-medycyna",
        patronage_type="profession",
        name_pl="Medycyna",
        name_en="Medicine",
        status=PatronageConceptStatus.APPROVED.value,
    )
    db_session.add_all([reviewed_source, legacy_source, concept])
    await db_session.flush()
    db_session.add_all(
        [
            ConceptAlias(
                concept_id=concept.id,
                value="Doktorzy",
                normalized_value="doktorzy",
                language_code="pl",
                alias_kind=ConceptAliasKind.COMMON.value,
            ),
            PersonPatronageConcept(
                person_id=reviewed_person.id,
                concept_id=concept.id,
                source_patronage_id=reviewed_source.id,
                source_patronage_type=reviewed_source.patronage_type,
                source_label=reviewed_source.name_pl,
                evidence_reference="Kwerenda redakcyjna",
                status=ConceptAssignmentStatus.APPROVED.value,
            ),
        ]
    )
    await db_session.commit()

    concepts = await async_client.get("/api/v1/taxonomy/patronages")
    assert concepts.status_code == 200
    assert concepts.headers["x-total-count"] == "2"
    assert concepts.json() == [
        {
            "slug": "profession-lekarzy",
            "patronage_type": "profession",
            "name_pl": "Lekarzy",
            "name_en": "Doctors",
            "description": None,
            "person_count": 1,
        },
        {
            "slug": "profession-medycyna",
            "patronage_type": "profession",
            "name_pl": "Medycyna",
            "name_en": "Medicine",
            "description": None,
            "person_count": 1,
        },
    ]

    alias_search = await async_client.get(
        "/api/v1/taxonomy/patronages", params={"search": "Doktorzy"}
    )
    assert alias_search.status_code == 200
    assert [item["slug"] for item in alias_search.json()] == ["profession-medycyna"]

    reviewed_persons = await async_client.get(
        "/api/v1/taxonomy/patronages/profession-medycyna/persons"
    )
    assert reviewed_persons.status_code == 200
    assert reviewed_persons.json()["total"] == 1
    assert [item["slug"] for item in reviewed_persons.json()["items"]] == ["sw-reviewed-patron"]

    legacy_persons = await async_client.get(
        "/api/v1/taxonomy/patronages/profession-lekarzy/persons"
    )
    assert legacy_persons.status_code == 200
    assert legacy_persons.json()["total"] == 1
    assert [item["slug"] for item in legacy_persons.json()["items"]] == ["sw-legacy-patron"]


@pytest.mark.asyncio
async def test_public_patronages_keep_source_slug_compatibility_after_full_review(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = Person(
        slug="sw-reviewed-source-slug",
        canonical_name="Święty Patron Źródłowy",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
    )
    db_session.add(person)
    await db_session.flush()
    source = Patronage(
        person_id=person.id,
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
    )
    concept = PatronageConcept(
        slug="profession-medycyna",
        patronage_type="profession",
        name_pl="Medycyna",
        name_en="Medicine",
        status=PatronageConceptStatus.APPROVED.value,
    )
    db_session.add_all([source, concept])
    await db_session.flush()
    db_session.add(
        PersonPatronageConcept(
            person_id=person.id,
            concept_id=concept.id,
            source_patronage_id=source.id,
            source_patronage_type=source.patronage_type,
            source_label=source.name_pl,
            evidence_reference="Kwerenda redakcyjna",
            status=ConceptAssignmentStatus.APPROVED.value,
        )
    )
    await db_session.commit()

    source_slug = await async_client.get("/api/v1/taxonomy/patronages/profession-lekarzy/persons")
    assert source_slug.status_code == 200
    assert source_slug.json()["concept"]["slug"] == "profession-medycyna"
    assert source_slug.json()["total"] == 1
    assert [item["slug"] for item in source_slug.json()["items"]] == ["sw-reviewed-source-slug"]


@pytest.mark.asyncio
async def test_public_patronages_merge_reviewed_and_unreviewed_people_for_same_label(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    reviewed_person = Person(
        slug="sw-reviewed-same-label",
        canonical_name="Święty Patron Zmapowany",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
    )
    unreviewed_person = Person(
        slug="sw-unreviewed-same-label",
        canonical_name="Święty Patron Bez Mapowania",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
    )
    db_session.add_all([reviewed_person, unreviewed_person])
    await db_session.flush()
    reviewed_source = Patronage(
        person_id=reviewed_person.id,
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
    )
    unreviewed_source = Patronage(
        person_id=unreviewed_person.id,
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
    )
    concept = PatronageConcept(
        slug="profession-lekarzy",
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
        status=PatronageConceptStatus.APPROVED.value,
    )
    db_session.add_all([reviewed_source, unreviewed_source, concept])
    await db_session.flush()
    db_session.add(
        PersonPatronageConcept(
            person_id=reviewed_person.id,
            concept_id=concept.id,
            source_patronage_id=reviewed_source.id,
            source_patronage_type=reviewed_source.patronage_type,
            source_label=reviewed_source.name_pl,
            evidence_reference="Kwerenda redakcyjna",
            status=ConceptAssignmentStatus.APPROVED.value,
        )
    )
    await db_session.commit()

    concepts = await async_client.get("/api/v1/taxonomy/patronages")
    assert concepts.status_code == 200
    assert concepts.json()[0]["slug"] == "profession-lekarzy"
    assert concepts.json()[0]["person_count"] == 2

    persons = await async_client.get("/api/v1/taxonomy/patronages/profession-lekarzy/persons")
    assert persons.status_code == 200
    assert persons.json()["total"] == 2
    assert [item["slug"] for item in persons.json()["items"]] == [
        "sw-unreviewed-same-label",
        "sw-reviewed-same-label",
    ]
