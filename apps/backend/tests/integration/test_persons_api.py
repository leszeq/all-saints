"""
Integration tests for Person API endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema, PersonUpdateSchema
from src.application.services.person_service import PersonService
from src.application.services.publication_revision_service import PublicationRevisionService
from src.domain.geography.models import Country, ReligiousOrder
from src.domain.hagiography.models import (
    Gender,
    Occupation,
    Person,
    PersonOccupation,
    PersonOrder,
    PersonTranslation,
    PersonType,
    PublicationRevision,
    PublicationRevisionStatus,
    PublicationStatus,
)
from src.domain.sources.models import Image


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

    search_response = await async_client.get(
        "/api/v1/persons", params={"search": "San Giovanni di Test"}
    )
    assert search_response.status_code == 200
    assert search_response.json()["items"][0]["search_reason"] == "translation_exact"
    assert search_response.json()["items"][0]["search_match"] == "San Giovanni di Test"


@pytest.mark.asyncio
async def test_public_person_reads_use_selected_revision_scalars_with_legacy_fallback(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Nazwa Live",
            summary_pl="Opis z pól live",
            person_type="saint",
            gender="male",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    revision = PublicationRevision(
        person_id=person.id,
        revision_number=1,
        status=PublicationRevisionStatus.PUBLISHED.value,
        base_version=person.version,
        payload={
            "canonical_name": "Św. Nazwa z rewizji",
            "summary_pl": "Opis z wybranej rewizji",
            "person_type": "blessed",
            "gender": "female",
            "era": "modern",
            "birth_year": 1900,
            "is_featured": True,
        },
    )
    db_session.add(revision)
    await db_session.flush()
    person.published_revision_id = revision.id
    await db_session.commit()

    detail_response = await async_client.get(f"/api/v1/persons/{person.slug}")
    list_response = await async_client.get("/api/v1/persons")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["canonical_name"] == "Św. Nazwa z rewizji"
    assert detail["summary_pl"] == "Opis z wybranej rewizji"
    assert detail["localized_content"]["summary"] == "Opis z wybranej rewizji"
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["canonical_name"] == "Św. Nazwa z rewizji"
    assert list_response.json()["items"][0]["summary_pl"] == "Opis z wybranej rewizji"
    assert list_response.json()["items"][0]["person_type"] == "blessed"
    assert (
        await async_client.get("/api/v1/persons", params={"person_type": "blessed"})
    ).json()["total"] == 1
    assert (
        await async_client.get("/api/v1/persons", params={"person_type": "saint"})
    ).json()["total"] == 0
    assert (
        await async_client.get("/api/v1/persons", params={"gender": "female"})
    ).json()["total"] == 1
    assert (
        await async_client.get("/api/v1/persons", params={"is_featured": "true"})
    ).json()["total"] == 1
    revision_search_response = await async_client.get(
        "/api/v1/persons",
        params={"search": "Św. Nazwa z rewizji"},
    )
    assert revision_search_response.status_code == 200
    assert revision_search_response.json()["total"] == 1
    assert revision_search_response.json()["items"][0]["canonical_name"] == (
        "Św. Nazwa z rewizji"
    )


@pytest.mark.asyncio
async def test_public_person_read_stays_on_published_revision_while_draft_changes(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Wersja publiczna",
            summary_pl="Streszczenie opublikowane",
            biography_pl="Biogram opublikowany",
            person_type="saint",
            gender="male",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    await db_session.flush()

    published_revision = PublicationRevision(
        person_id=person.id,
        revision_number=1,
        status=PublicationRevisionStatus.PUBLISHED.value,
        base_version=person.version,
        payload={
            "canonical_name": person.canonical_name,
            "summary_pl": person.summary_pl,
            "biography_pl": person.biography_pl,
            "person_type": person.person_type,
            "gender": person.gender,
        },
    )
    db_session.add(published_revision)
    await db_session.flush()
    person.published_revision_id = published_revision.id
    await db_session.commit()

    revision_service = PublicationRevisionService(db_session)
    draft = await revision_service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    await revision_service.update_draft(
        draft.id,
        expected_version=draft.version,
        changes={
            "summary_pl": "Streszczenie tylko w aktywnym drafcie",
            "biography_pl": "Biogram tylko w aktywnym drafcie",
        },
        author_id=None,
    )
    await db_session.commit()

    response = await async_client.get(f"/api/v1/persons/{person.slug}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_name"] == "Św. Wersja publiczna"
    assert payload["summary_pl"] == "Streszczenie opublikowane"
    assert payload["biography_pl"] == "Biogram opublikowany"
    assert "Streszczenie tylko w aktywnym drafcie" not in response.text
    assert "Biogram tylko w aktywnym drafcie" not in response.text


@pytest.mark.asyncio
async def test_public_person_reads_order_memberships_from_selected_revision(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Św. Zakon z rewizji")
    )
    person.status = PublicationStatus.PUBLISHED.value
    selected_order = ReligiousOrder(
        id=uuid.uuid4(),
        slug="wybrany-zakon-z-rewizji",
        name="Zakon z wybranej rewizji",
    )
    live_order = ReligiousOrder(
        id=uuid.uuid4(),
        slug="zakon-z-pol-live",
        name="Zakon z pól live",
    )
    db_session.add_all([selected_order, live_order])
    await db_session.flush()
    db_session.add(PersonOrder(person_id=person.id, order_id=live_order.id))
    revision = PublicationRevision(
        person_id=person.id,
        revision_number=1,
        status=PublicationRevisionStatus.PUBLISHED.value,
        base_version=person.version,
        payload={
            "orders": [
                {
                    "order_id": str(selected_order.id),
                    "entry_date": "1500",
                    "exit_date": None,
                    "is_founder": True,
                    "membership_type": "founder",
                    "notes": "Notatka z rewizji",
                }
            ]
        },
    )
    db_session.add(revision)
    await db_session.flush()
    person.published_revision_id = revision.id
    await db_session.commit()

    response = await async_client.get(f"/api/v1/persons/{person.slug}")

    assert response.status_code == 200
    orders = response.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["order"]["name"] == "Zakon z wybranej rewizji"
    assert orders[0]["entry_date"] == "1500"
    assert orders[0]["is_founder"] is True
    assert "Zakon z pól live" not in response.text

    selected_order_filter = await async_client.get(
        "/api/v1/persons", params={"order_id": str(selected_order.id)}
    )
    live_order_filter = await async_client.get(
        "/api/v1/persons", params={"order_id": str(live_order.id)}
    )
    assert selected_order_filter.status_code == 200
    assert selected_order_filter.json()["total"] == 1
    assert live_order_filter.status_code == 200
    assert live_order_filter.json()["total"] == 0
    selected_order_facets = await async_client.get(
        "/api/v1/persons/facets", params={"order_id": str(selected_order.id)}
    )
    assert selected_order_facets.status_code == 200
    assert selected_order_facets.json()["total"] == 1
    assert selected_order_facets.json()["orders"] == [
        {"id": str(selected_order.id), "count": 1}
    ]


@pytest.mark.asyncio
async def test_public_person_reads_avatar_from_selected_revision_images(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Św. Avatar z rewizji")
    )
    person.status = PublicationStatus.PUBLISHED.value
    live_image = Image(
        person_id=person.id,
        url="https://example.org/live-avatar.jpg",
        license="public_domain",
        is_primary=True,
    )
    db_session.add(live_image)
    await db_session.flush()
    selected_image_id = uuid.uuid4()
    revision = PublicationRevision(
        person_id=person.id,
        revision_number=1,
        status=PublicationRevisionStatus.PUBLISHED.value,
        base_version=person.version,
        payload={
            "images": [
                {
                    "id": str(selected_image_id),
                    "url": "https://example.org/revision-avatar.jpg",
                    "thumbnail_url": "https://example.org/revision-avatar-thumb.jpg",
                    "title": "Portret z rewizji",
                    "license": "cc_by",
                    "photographer": "Autor rewizji",
                    "source_url": "https://example.org/image-source",
                    "is_primary": True,
                    "sort_order": 0,
                }
            ]
        },
    )
    db_session.add(revision)
    await db_session.flush()
    person.published_revision_id = revision.id
    await db_session.commit()

    detail_response = await async_client.get(f"/api/v1/persons/{person.slug}")
    list_response = await async_client.get("/api/v1/persons")

    assert detail_response.status_code == 200
    assert detail_response.json()["avatar"]["id"] == str(selected_image_id)
    assert detail_response.json()["avatar"]["url"] == "https://example.org/revision-avatar.jpg"
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["avatar"]["url"] == (
        "https://example.org/revision-avatar.jpg"
    )
    assert "live-avatar.jpg" not in detail_response.text


@pytest.mark.asyncio
async def test_public_person_reads_typed_relations_from_selected_revision(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Relacje z rewizji",
            aliases=[{"value": "Alias live", "language_code": "pl"}],
            patronages=[{"patronage_type": "city", "name_pl": "Miasta live"}],
            beatification={"beatification_year": 1900},
            canonization={"canonization_year": 1910},
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    await db_session.flush()

    revision = PublicationRevision(
        person_id=person.id,
        revision_number=1,
        status=PublicationRevisionStatus.PUBLISHED.value,
        base_version=person.version,
        payload={
            "aliases": [
                {
                    "id": str(uuid.uuid4()),
                    "value": "Alias z rewizji",
                    "normalized_value": "alias z rewizji",
                    "language_code": "pl",
                    "kind": "alias",
                }
            ],
            "patronages": [
                {
                    "id": str(uuid.uuid4()),
                    "patronage_type": "profession",
                    "name_pl": "Zawodu z rewizji",
                    "name_en": "Revision profession",
                    "description": "Opis z rewizji",
                    "is_official": True,
                }
            ],
            "beatification": {
                "id": str(uuid.uuid4()),
                "beatification_date": "1950-01-01",
                "beatification_year": 1950,
            },
            "canonization": {
                "id": str(uuid.uuid4()),
                "canonization_date": "1960-01-01",
                "canonization_year": 1960,
            },
        },
    )
    db_session.add(revision)
    await db_session.flush()
    person.published_revision_id = revision.id
    await db_session.commit()

    detail_response = await async_client.get(f"/api/v1/persons/{person.slug}")
    list_response = await async_client.get("/api/v1/persons")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["aliases"][0]["value"] == "Alias z rewizji"
    assert detail["patronages"][0]["name_pl"] == "Zawodu z rewizji"
    assert detail["beatification"]["beatification_year"] == 1950
    assert detail["canonization"]["canonization_year"] == 1960
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["patronages"][0]["name_pl"] == (
        "Zawodu z rewizji"
    )
    assert "Miasta live" not in detail_response.text

    alias_search = await async_client.get(
        "/api/v1/persons", params={"search": "Alias z rewizji"}
    )
    patronage_search = await async_client.get(
        "/api/v1/persons", params={"search": "Zawodu z rewizji"}
    )
    stale_alias_search = await async_client.get(
        "/api/v1/persons", params={"search": "Alias live"}
    )
    stale_patronage_search = await async_client.get(
        "/api/v1/persons", params={"search": "Miasta live"}
    )
    assert alias_search.status_code == 200
    assert alias_search.json()["total"] == 1
    assert patronage_search.status_code == 200
    assert patronage_search.json()["total"] == 1
    assert stale_alias_search.status_code == 200
    assert stale_alias_search.json()["total"] == 0
    assert stale_patronage_search.status_code == 200
    assert stale_patronage_search.json()["total"] == 0

    revision_patronage_filter = await async_client.get(
        "/api/v1/persons", params={"patronage": "work"}
    )
    assert revision_patronage_filter.status_code == 200
    assert revision_patronage_filter.json()["total"] == 1


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
        allow_published_update=True,
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

    searched_facets = await async_client.get(
        "/api/v1/persons/facets",
        params={"search": "Pasująca"},
    )
    assert searched_facets.status_code == 200
    assert searched_facets.json()["total"] == 1
