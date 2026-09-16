"""Integration coverage for source catalogue application boundaries."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.source_catalogue import (
    CreateBibliographyCommand,
    CreateHistoricalSourceCommand,
    UpdateBibliographyCommand,
    UpdateHistoricalSourceCommand,
)
from src.application.services.source_catalogue_service import SourceCatalogueService
from src.domain.hagiography.models import Gender, Person, PersonType, PublicationStatus
from src.domain.sources.models import Bibliography, Image, PersonSource


async def test_source_catalogue_creates_and_filters_both_source_kinds(
    db_session: AsyncSession,
) -> None:
    service = SourceCatalogueService(db_session)
    bibliography = await service.create_bibliography(
        CreateBibliographyCommand(
            title="Martyrologium Romanum",
            authors="Dicasterium de Cultu Divino",
            year=2004,
        )
    )
    await service.create_bibliography(CreateBibliographyCommand(title="Acta Sanctorum", year=1643))
    historical_source = await service.create_historical_source(
        CreateHistoricalSourceCommand(
            title="Vita sancti testis",
            repository="Archivum Romanum",
            is_digitized=True,
            digitization_url="https://example.test/vita",
        )
    )

    bibliography_items, bibliography_total = await service.list_bibliography(
        search="Dicasterium",
        page=1,
        per_page=10,
    )
    historical_items, historical_total = await service.list_historical_sources(
        search="Archivum",
        page=1,
        per_page=10,
    )

    assert bibliography_total == 1
    assert [item.id for item in bibliography_items] == [bibliography.id]
    assert historical_total == 1
    assert [item.id for item in historical_items] == [historical_source.id]


async def test_source_catalogue_updates_links_without_replacing_records(
    db_session: AsyncSession,
) -> None:
    service = SourceCatalogueService(db_session)
    bibliography = await service.create_bibliography(
        CreateBibliographyCommand(title="Rita da Cascia", source_type="website")
    )
    historical_source = await service.create_historical_source(
        CreateHistoricalSourceCommand(title="Vita sanctae Ritae")
    )

    updated_bibliography = await service.update_bibliography(
        bibliography.id,
        UpdateBibliographyCommand(
            url="https://www.santiebeati.it/dettaglio/56950",
            url_access_date="2026-09-14",
            reliability_score=5,
        ),
    )
    updated_historical = await service.update_historical_source(
        historical_source.id,
        UpdateHistoricalSourceCommand(
            digitization_url="https://archive.example.test/vita-ritae",
            is_digitized=True,
        ),
    )

    assert updated_bibliography.id == bibliography.id
    assert updated_bibliography.url == "https://www.santiebeati.it/dettaglio/56950"
    assert updated_bibliography.url_access_date == "2026-09-14"
    assert updated_bibliography.reliability_score == 5
    assert updated_historical.id == historical_source.id
    assert updated_historical.digitization_url == "https://archive.example.test/vita-ritae"
    assert updated_historical.is_digitized is True


async def test_public_source_stats_exclude_unpublished_person_relations(
    db_session: AsyncSession,
) -> None:
    published = Person(
        slug="sw-opublikowane-zrodla",
        canonical_name="Św. Opublikowane Źródła",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.UNKNOWN.value,
    )
    draft = Person(
        slug="szkic-prywatnych-zrodel",
        canonical_name="Szkic Prywatnych Źródeł",
        person_type=PersonType.CANDIDATE.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
    )
    bibliography = Bibliography(title="Źródło statystyk publicznych")
    db_session.add_all([published, draft, bibliography])
    await db_session.flush()
    db_session.add_all(
        [
            PersonSource(person_id=published.id, bibliography_id=bibliography.id),
            PersonSource(person_id=draft.id, bibliography_id=bibliography.id),
            Image(
                person_id=published.id,
                url="https://example.test/published.jpg",
                license="unknown",
            ),
            Image(
                person_id=draft.id,
                url="https://example.test/draft.jpg",
                license="unknown",
            ),
        ]
    )
    await db_session.flush()

    stats = await SourceCatalogueService(db_session).get_public_stats()

    assert stats.total_published_persons == 1
    assert stats.documented_persons == 1
    assert stats.person_source_links == 1
    assert stats.bibliography_sources == 1
    assert stats.historical_sources == 0
    assert stats.images == 1
    assert stats.unknown_license_images == 1
