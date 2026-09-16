"""Public citations expose only active assignments on published profiles."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
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
