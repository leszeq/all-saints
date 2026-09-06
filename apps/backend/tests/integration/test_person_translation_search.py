"""PostgreSQL search coverage for active localized person content."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonTranslation, PublicationStatus


@pytest.mark.asyncio
async def test_search_finds_translated_content_without_duplicates_or_deleted_hits(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(
        PersonCreateSchema(
            canonical_name="Św. Poszukiwany przez tłumaczenie",
            person_type="saint",
            gender="unknown",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    db_session.add_all(
        [
            PersonTranslation(
                person_id=person.id,
                language_code="it",
                canonical_name="San Ricercabile",
                summary="Assistenza agli ammalati negli ospedali medievali.",
                biography="Sviluppò una rete di ospizi per pellegrini.",
            ),
            PersonTranslation(
                person_id=person.id,
                language_code="de",
                canonical_name="Heiliger Auffindbar",
                summary="Die Hospizpflege prägte sein Wirken.",
                biography="Er kümmerte sich auch um Seefahrer.",
            ),
            PersonTranslation(
                person_id=person.id,
                language_code="fr",
                canonical_name="Saint Introuvable",
                summary="Motsecretinvisible dans une traduction supprimée.",
                deleted_at=person.updated_at,
            ),
        ]
    )
    await db_session.flush()
    # Test metadata is created without Alembic triggers, so emulate the trigger's
    # deterministic backfill before exercising the production query.
    await db_session.execute(
        text("""
            UPDATE person_translations
            SET search_vector =
                setweight(to_tsvector('simple', unaccent(coalesce(canonical_name, ''))), 'A') ||
                setweight(to_tsvector('simple', unaccent(coalesce(summary, ''))), 'B') ||
                setweight(to_tsvector('simple', unaccent(coalesce(iconographic_attributes, ''))), 'B') ||
                setweight(to_tsvector('simple', unaccent(coalesce(prayers, ''))), 'C') ||
                setweight(to_tsvector('simple', unaccent(coalesce(biography, ''))), 'D')
            WHERE person_id = :person_id
            """),
        {"person_id": person.id},
    )
    await db_session.commit()

    for phrase in ("ammalati ospedali", "Seefahrer", "Hospizpflege"):
        results, total = await service.list_persons(
            search=phrase,
            published_only=True,
        )
        assert total == 1
        assert [result.id for result in results] == [person.id]

    deleted_results, deleted_total = await service.list_persons(
        search="Motsecretinvisible",
        published_only=True,
    )
    assert deleted_total == 0
    assert deleted_results == []

    localized_response = await async_client.get(
        "/api/v1/persons",
        params={"search": "ammalati ospedali", "locale": "it-IT"},
    )
    assert localized_response.status_code == 200
    payload = localized_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["localized_content"]["canonical_name"] == "San Ricercabile"
    assert payload["items"][0]["localized_content"]["resolved_locale"] == "it"


@pytest.mark.asyncio
async def test_multiple_matching_translations_do_not_duplicate_a_person(
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(
        PersonCreateSchema(
            canonical_name="Św. Jeden Wynik",
            person_type="saint",
            gender="unknown",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    db_session.add_all(
        [
            PersonTranslation(
                person_id=person.id,
                language_code="it",
                canonical_name="San Unico",
                summary="Parolacomune",
                search_vector="'parolacomune':1A",
            ),
            PersonTranslation(
                person_id=person.id,
                language_code="de",
                canonical_name="Heiliger Einzig",
                summary="Parolacomune",
                search_vector="'parolacomune':1A",
            ),
        ]
    )
    await db_session.commit()

    results, total = await service.list_persons(
        search="Parolacomune",
        published_only=True,
        page=1,
        per_page=1,
    )

    assert total == 1
    assert [result.id for result in results] == [person.id]
