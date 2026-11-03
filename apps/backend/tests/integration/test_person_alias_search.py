"""PostgreSQL integration coverage for person aliases and translated names."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Patronage, PersonTranslation, PublicationStatus


@pytest.mark.asyncio
async def test_catalogue_search_finds_aliases_and_translated_names(
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(
        PersonCreateSchema.model_validate(
            {
                "canonical_name": "Św. Jan Paweł II",
                "person_type": "saint",
                "status": "draft",
                "gender": "male",
                "aliases": [
                    {
                        "value": "Karol Wojtyła",
                        "kind": "birth_name",
                        "language_code": "pl",
                    },
                    {
                        "value": "JPII",
                        "kind": "abbreviation",
                        "language_code": "pl",
                    },
                ],
            }
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    db_session.add(
        PersonTranslation(
            person_id=person.id,
            language_code="de",
            canonical_name="Johannes Paul II.",
        )
    )
    await db_session.commit()

    expected_matches = {
        "Karol Wojtyla": ("alias_exact", "Karol Wojtyła"),
        "JPII": ("alias_exact", "JPII"),
        "Johannes Paul II": ("translation_exact", "Johannes Paul II."),
    }
    for phrase, (expected_reason, expected_match) in expected_matches.items():
        results, total = await service.list_persons(
            search=phrase,
            published_only=True,
        )

        assert total == 1
        assert [result.id for result in results] == [person.id]
        assert results[0].search_reason == expected_reason
        assert results[0].search_match == expected_match

    loaded = await service.get_by_id_or_slug(str(person.id), published_only=True)
    assert loaded is not None
    assert {(alias.value, alias.normalized_value) for alias in loaded.aliases} == {
        ("Karol Wojtyła", "karol wojtyla"),
        ("JPII", "jpii"),
    }


@pytest.mark.asyncio
async def test_catalogue_search_prioritizes_exact_canonical_name(
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    exact = await service.create_person(
        PersonCreateSchema(canonical_name="Jan Paweł", person_type="saint", gender="male")
    )
    similar = await service.create_person(
        PersonCreateSchema(canonical_name="Jan Paweł Wielki", person_type="saint", gender="male")
    )
    exact.status = PublicationStatus.PUBLISHED.value
    similar.status = PublicationStatus.PUBLISHED.value
    await db_session.commit()

    results, total = await service.list_persons(search="Jan Paweł", published_only=True)

    assert total == 2
    assert results[0].id == exact.id
    assert results[0].search_reason == "canonical_exact"
    assert results[0].search_match == "Jan Paweł"


@pytest.mark.asyncio
async def test_catalogue_search_finds_active_patronage_without_deleted_hits(
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(
        PersonCreateSchema(
            canonical_name="Św. Patronat Aktywny",
            person_type="saint",
            gender="unknown",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    db_session.add_all(
        [
            Patronage(
                person_id=person.id,
                patronage_type="profession",
                name_pl="Opiekun lekarzy",
            ),
            Patronage(
                person_id=person.id,
                patronage_type="profession",
                name_pl="Usunięty termin medyczny",
                deleted_at=person.updated_at,
            ),
        ]
    )
    await db_session.commit()

    active_results, active_total = await service.list_persons(
        search="lekarzy",
        published_only=True,
    )
    assert active_total == 1
    assert [result.id for result in active_results] == [person.id]

    deleted_results, deleted_total = await service.list_persons(
        search="medyczny",
        published_only=True,
    )
    assert deleted_total == 0
    assert deleted_results == []
