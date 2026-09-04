"""PostgreSQL integration coverage for person aliases and translated names."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonTranslation, PublicationStatus
from src.presentation.api.v1.persons.schemas import PersonCreateSchema


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

    for phrase in ("Karol Wojtyla", "JPII", "Johannes Paul II"):
        results, total = await service.list_persons(
            search=phrase,
            published_only=True,
        )

        assert total == 1
        assert [result.id for result in results] == [person.id]

    loaded = await service.get_by_id_or_slug(str(person.id), published_only=True)
    assert loaded is not None
    assert {(alias.value, alias.normalized_value) for alias in loaded.aliases} == {
        ("Karol Wojtyła", "karol wojtyla"),
        ("JPII", "jpii"),
    }
