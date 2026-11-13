"""Public citations expose only active assignments on published profiles."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PublicationRevision, PublicationRevisionStatus
from src.domain.sources.models import Bibliography, HistoricalSource, PersonSource


@pytest.mark.asyncio
async def test_public_citations_include_verifiable_facts_without_editorial_data(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(PersonCreateSchema(canonical_name="Św. Rita — źródła"))
    person.status = "published"
    other = await service.create_person(PersonCreateSchema(canonical_name="Inny profil ze źródłem"))
    now = datetime.now(UTC)
    book = Bibliography(
        title="Życie św. Rity",
        authors="Autor opracowania",
        publisher="Wydawnictwo",
        year=2001,
        isbn="9780000000001",
        doi="10.1234/rita",
        url="https://example.org/rita",
        notes="WEWNĘTRZNA NOTATKA",
        reliability_score=2,
        abstract="WEWNĘTRZNY OPIS",
    )
    historical = HistoricalSource(
        title="Akta historyczne",
        repository="Biblioteka",
        call_number="MS 123",
        date_range="1450–1460",
        digitization_url="https://example.org/skan",
        description="WEWNĘTRZNY OPIS ARCHIWUM",
    )
    removed = Bibliography(title="Usunięta bibliografia", deleted_at=now)
    removed_historical = HistoricalSource(title="Usunięte archiwum", deleted_at=now)
    unrelated = Bibliography(title="Źródło innego profilu")
    db_session.add_all([book, historical, removed, removed_historical, unrelated])
    await db_session.flush()
    db_session.add_all(
        [
            PersonSource(
                person_id=person.id,
                bibliography_id=book.id,
                is_primary=True,
                page_reference="s. 12–18",
                notes="WEWNĘTRZNA UWAGA",
                relevance_score=1,
                quote="NIEPUBLICZNY CYTAT",
            ),
            PersonSource(person_id=person.id, historical_source_id=historical.id),
            PersonSource(person_id=person.id, bibliography_id=removed.id),
            PersonSource(person_id=person.id, historical_source_id=removed_historical.id),
            PersonSource(person_id=person.id, bibliography_id=unrelated.id, deleted_at=now),
            PersonSource(person_id=other.id, bibliography_id=unrelated.id),
            PersonSource(person_id=person.id),
        ]
    )
    await db_session.commit()
    response = await async_client.get(f"/api/v1/persons/{person.slug}")
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert len(sources) == 2
    assert sources[0]["is_primary"]
    assert sources[0]["page_reference"] == "s. 12–18"
    assert sources[0]["bibliography"]["authors"] == "Autor opracowania"
    assert sources[0]["bibliography"]["doi"] == "10.1234/rita"
    assert sources[0]["bibliography"]["url"] == "https://example.org/rita"
    assert sources[1]["historical_source"]["call_number"] == "MS 123"
    assert sources[1]["historical_source"]["digitization_url"] == "https://example.org/skan"
    assert response.json()["source_summary"] == {
        "total": 2,
        "primary": 1,
        "with_online_link": 2,
    }
    assert response.json()["sources_page"] == 1
    assert response.json()["sources_per_page"] == 24
    assert response.json()["sources_pages"] == 1
    assert response.json()["quality_summary"] == {
        "has_summary": False,
        "has_biography": False,
        "has_recognition": False,
        "has_relational_context": False,
    }
    for private in (
        "WEWNĘTRZ",
        "NIEPUBLICZNY",
        "reliability_score",
        "relevance_score",
        '"quote"',
        '"notes"',
    ):
        assert private not in response.text
    # The editorial source endpoint remains protected.
    protected = await async_client.get(f"/api/v1/sources/person-links/{person.id}")
    assert protected.status_code == 401


@pytest.mark.asyncio
async def test_public_citations_follow_selected_revision_snapshot(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Św. Źródła z rewizji")
    )
    person.status = "published"
    selected = Bibliography(
        title="Źródło wybrane przez rewizję",
        url="https://example.org/revision-source",
    )
    live = Bibliography(title="Źródło z pól live")
    db_session.add_all([selected, live])
    await db_session.flush()
    db_session.add(PersonSource(person_id=person.id, bibliography_id=live.id))
    revision = PublicationRevision(
        person_id=person.id,
        revision_number=1,
        status=PublicationRevisionStatus.PUBLISHED.value,
        base_version=person.version,
        payload={
            "sources": [
                {
                    "id": str(uuid.uuid4()),
                    "bibliography_id": str(selected.id),
                    "page_reference": "s. 44",
                    "is_primary": True,
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
    sources = response.json()["sources"]
    assert len(sources) == 1
    assert sources[0]["page_reference"] == "s. 44"
    assert sources[0]["is_primary"] is True
    assert sources[0]["bibliography"]["title"] == "Źródło wybrane przez rewizję"
    assert sources[0]["bibliography"]["url"] == "https://example.org/revision-source"
    assert "Źródło z pól live" not in response.text
    assert response.json()["source_summary"] == {
        "total": 1,
        "primary": 1,
        "with_online_link": 1,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,deleted",
    [("draft", False), ("review", False), ("archived", False), ("published", True)],
)
async def test_hidden_profiles_never_expose_citations(
    db_session: AsyncSession,
    async_client: AsyncClient,
    status: str,
    deleted: bool,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Ukryty profil")
    )
    person.status = status
    if deleted:
        person.deleted_at = datetime.now(UTC)
    book = Bibliography(title="Poufne źródło szkicu")
    db_session.add(book)
    await db_session.flush()
    db_session.add(PersonSource(person_id=person.id, bibliography_id=book.id))
    await db_session.commit()
    for identifier in (str(person.id), person.slug):
        response = await async_client.get(f"/api/v1/persons/{identifier}")
        assert response.status_code == 404
        assert "Poufne" not in response.text


@pytest.mark.asyncio
async def test_published_profile_without_sources_returns_empty_list(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Profil bez źródeł")
    )
    person.status = "published"
    await db_session.commit()
    response = await async_client.get(f"/api/v1/persons/{person.slug}")
    assert response.status_code == 200
    assert response.json()["sources"] == []


@pytest.mark.asyncio
async def test_public_profile_sources_are_paginated_without_changing_aggregates(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Profil z paginowanymi źródłami")
    )
    person.status = "published"
    sources = [
        Bibliography(title="Źródło pierwsze", url="https://example.org/one"),
        Bibliography(title="Źródło drugie", doi="10.1234/two"),
        Bibliography(title="Źródło trzecie"),
    ]
    db_session.add_all(sources)
    await db_session.flush()
    created_at = datetime(2020, 1, 1, tzinfo=UTC)
    db_session.add_all(
        [
            PersonSource(
                person_id=person.id,
                bibliography_id=sources[0].id,
                is_primary=True,
                created_at=created_at,
            ),
            PersonSource(
                person_id=person.id,
                bibliography_id=sources[1].id,
                created_at=created_at + timedelta(seconds=1),
            ),
            PersonSource(
                person_id=person.id,
                bibliography_id=sources[2].id,
                created_at=created_at + timedelta(seconds=2),
            ),
        ]
    )
    await db_session.commit()

    response = await async_client.get(
        f"/api/v1/persons/{person.slug}",
        params={"sources_page": 2, "sources_per_page": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [source["bibliography"]["title"] for source in payload["sources"]] == ["Źródło drugie"]
    assert payload["sources_page"] == 2
    assert payload["sources_per_page"] == 1
    assert payload["sources_pages"] == 3
    assert payload["source_summary"] == {
        "total": 3,
        "primary": 1,
        "with_online_link": 2,
    }
