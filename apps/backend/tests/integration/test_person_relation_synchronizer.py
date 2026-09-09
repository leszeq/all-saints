"""Integration coverage for person relation synchronization through mutations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema, PersonUpdateSchema
from src.application.services.person_service import PersonService


async def test_person_create_and_update_synchronize_editable_relations(
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(
        PersonCreateSchema.model_validate(
            {
                "canonical_name": "Św. Testowa Relacja",
                "person_type": "saint",
                "gender": "female",
                "avatar": {
                    "url": "https://example.test/portrait.jpg",
                    "license": "public_domain",
                },
                "aliases": [
                    {
                        "value": "Testowa z Relacji",
                        "language_code": "PL",
                        "kind": "alias",
                    }
                ],
                "patronages": [
                    {
                        "patronage_type": "profession",
                        "name_pl": "Redaktorzy danych",
                        "is_official": False,
                    }
                ],
                "beatification": {"beatification_year": 2001},
                "canonization": {"canonization_year": 2005},
            }
        )
    )

    assert person.avatar is not None
    assert person.avatar.url == "https://example.test/portrait.jpg"
    assert [(alias.value, alias.language_code) for alias in person.aliases] == [
        ("Testowa z Relacji", "pl")
    ]
    assert [patronage.name_pl for patronage in person.patronages] == ["Redaktorzy danych"]
    assert person.beatification is not None
    assert person.beatification.beatification_year == 2001
    assert person.canonization is not None
    assert person.canonization.canonization_year == 2005

    updated = await service.update_person(
        person,
        PersonUpdateSchema.model_validate(
            {
                "expected_version": person.version,
                "avatar": None,
                "aliases": [
                    {
                        "value": "Relacyjna",
                        "language_code": "pl",
                        "kind": "religious_name",
                    }
                ],
                "patronages": [],
                "beatification": None,
                "canonization": {"canonization_year": 2006},
                "change_summary": "Aktualizacja relacji testowych",
            }
        ),
    )

    assert updated.avatar is None
    assert [(alias.value, alias.kind) for alias in updated.aliases] == [
        ("Relacyjna", "religious_name")
    ]
    assert updated.patronages == []
    assert updated.beatification is None
    assert updated.canonization is not None
    assert updated.canonization.canonization_year == 2006
