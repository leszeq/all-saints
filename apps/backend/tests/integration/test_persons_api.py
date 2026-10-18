"""
Integration tests for Person API endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema, PersonUpdateSchema
from src.application.services.person_service import PersonService
from src.domain.geography.models import Country, ReligiousOrder
from src.domain.hagiography.models import (
    Gender,
    Occupation,
    Person,
    PersonOccupation,
    PersonOrder,
    PersonTranslation,
    PersonType,
    PublicationStatus,
)


@pytest.mark.asyncio
async def test_list_persons_empty(async_client: AsyncClient):
    response = await async_client.get("/api/v1/persons")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_admin_path_is_not_captured_by_public_slug_route(async_client: AsyncClient):
    response = await async_client.get("/api/v1/persons/admin")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_nonexistent_person(async_client: AsyncClient):
    response = await async_client.get("/api/v1/persons/nonexistent-slug")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "NOT_FOUND"
    assert data["message"] == "Osoba nie została znaleziona"
    assert data["detail"] == "Osoba nie została znaleziona"
    assert data["request_id"] == response.headers["x-request-id"]


@pytest.mark.asyncio
async def test_public_person_endpoints_expose_explicit_localization_projection(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Jan Testowy",
            canonical_name_en="St. John Test",
            summary_pl="Polskie streszczenie",
            biography_pl="Polski biogram",
            person_type="saint",
            gender="male",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    db_session.add(
        PersonTranslation(
            person_id=person.id,
            language_code="it",
            canonical_name="San Giovanni di Test",
            summary="Sommario italiano",
            biography="Biografia italiana",
            iconographic_attributes="Giglio; libro",
        )
    )
    await db_session.commit()

    detail_response = await async_client.get(
        f"/api/v1/persons/{person.slug}", params={"locale": "it-IT"}
    )
    list_response = await async_client.get("/api/v1/persons", params={"locale": "it"})

    assert detail_response.status_code == 200
    assert detail_response.json()["localized_content"] == {
        "requested_locale": "it-it",
        "resolved_locale": "it",
        "fallback_used": True,
        "source": "translation",
        "canonical_name": "San Giovanni di Test",
        "summary": "Sommario italiano",
        "biography": "Biografia italiana",
        "prayers": None,
        "iconographic_attributes": "Giglio; libro",
    }
    assert list_response.status_code == 200
    list_content = list_response.json()["items"][0]["localized_content"]
    assert list_content["canonical_name"] == "San Giovanni di Test"
    assert list_content["iconographic_attributes"] == "Giglio; libro"
    assert "biography" not in list_content


@pytest.mark.asyncio
async def test_legacy_admin_edit_keeps_primary_translation_current(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(
        PersonCreateSchema(
            canonical_name="Św. Aktualizowany",
            summary_pl="Pierwsze streszczenie",
            biography_pl="Pierwszy biogram",
            person_type="saint",
            gender="male",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    translation = PersonTranslation(
        person_id=person.id,
        language_code="pl",
        canonical_name=person.canonical_name,
        summary=person.summary_pl,
        biography=person.biography_pl,
    )
    db_session.add(translation)
    await db_session.commit()
    await db_session.refresh(person)

    await service.update_person(
        person,
        PersonUpdateSchema(
            summary_pl="Streszczenie po edycji administratora",
            expected_version=person.version,
        ),
    )
    await db_session.commit()

    response = await async_client.get(f"/api/v1/persons/{person.slug}")

    assert response.status_code == 200
    assert response.json()["localized_content"]["summary"] == (
        "Streszczenie po edycji administratora"
    )
    await db_session.refresh(translation)
    assert translation.summary == "Streszczenie po edycji administratora"
    assert translation.version == 2


@pytest.mark.asyncio
async def test_public_person_locale_rejects_malformed_language_tag(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/persons", params={"locale": "not a locale"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_public_catalogue_relational_filters_and_facets_exclude_drafts(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    country = Country(
        id=uuid.uuid4(),
        name_pl="Polska testowa",
        name_en="Test Poland",
        iso_code_alpha2="TP",
        iso_code_alpha3="TST",
    )
    order = ReligiousOrder(id=uuid.uuid4(), slug="zakon-fasetowy", name="Zakon Fasetowy")
    occupation = Occupation(id=uuid.uuid4(), name_pl="Lekarz testowy", name_en="Test doctor")
    matching = Person(
        id=uuid.uuid4(),
        slug="sw-faseta-pasuje",
        canonical_name="Św. Pasująca Faseta",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.FEMALE.value,
        birth_country_id=country.id,
        nationality_id=country.id,
        birth_year=1890,
        death_year=1960,
    )
    order_only = Person(
        id=uuid.uuid4(),
        slug="sw-faseta-tylko-zakon",
        canonical_name="Św. Tylko Zakon",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.MALE.value,
        birth_year=1880,
        death_year=1950,
    )
    draft = Person(
        id=uuid.uuid4(),
        slug="draft-faseta",
        canonical_name="Draft Faseta",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.MALE.value,
        birth_year=1890,
        death_year=1960,
    )
    db_session.add_all([country, order, occupation, matching, order_only, draft])
    await db_session.flush()
    db_session.add_all(
        [
            PersonOrder(person_id=matching.id, order_id=order.id),
            PersonOrder(person_id=order_only.id, order_id=order.id),
            PersonOrder(person_id=draft.id, order_id=order.id),
            PersonOccupation(person_id=matching.id, occupation_id=occupation.id),
        ]
    )
    await db_session.commit()

    filtered = await async_client.get(
        "/api/v1/persons",
        params={
            "order_id": str(order.id),
            "occupation_id": str(occupation.id),
            "birth_year_from": 1885,
            "birth_year_to": 1900,
            "nationality_id": str(country.id),
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["slug"] == matching.slug

    facets = await async_client.get("/api/v1/persons/facets")
    assert facets.status_code == 200
    facet_data = facets.json()
    assert facet_data["total"] == 2
    assert facet_data["orders"] == [{"id": str(order.id), "count": 2}]
    assert facet_data["occupations"] == [{"id": str(occupation.id), "count": 1}]
    assert facet_data["birth_countries"] == [{"id": str(country.id), "count": 1}]
    assert facet_data["nationalities"] == [{"id": str(country.id), "count": 1}]
