"""
Integration tests for Person API endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonTranslation, PublicationStatus


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
async def test_public_person_locale_rejects_malformed_language_tag(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/persons", params={"locale": "not a locale"})

    assert response.status_code == 422
