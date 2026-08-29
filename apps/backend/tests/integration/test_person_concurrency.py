"""Integration coverage for concurrent editorial updates."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.application.services.person_service import (
    PersonService,
    PersonVersionConflictError,
)
from src.domain.hagiography.models import Gender, Person, PersonType, PublicationStatus
from src.presentation.api.v1.persons.schemas import PersonUpdateSchema


@pytest.mark.asyncio
async def test_stale_editor_cannot_overwrite_a_newer_person_version(test_engine) -> None:
    person_id = uuid.uuid4()
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as setup_session:
        setup_session.add(
            Person(
                id=person_id,
                slug="sw-test-konkurencji",
                canonical_name="Św. Test Konkurencji",
                person_type=PersonType.SAINT.value,
                status=PublicationStatus.DRAFT.value,
                gender=Gender.UNKNOWN.value,
                version=1,
            )
        )
        await setup_session.commit()

    async with session_factory() as first_session, session_factory() as stale_session:
        first_person = (
            await first_session.execute(select(Person).where(Person.id == person_id))
        ).scalar_one()
        stale_person = (
            await stale_session.execute(select(Person).where(Person.id == person_id))
        ).scalar_one()

        await PersonService(first_session).update_person(
            first_person,
            PersonUpdateSchema(summary_pl="Zmiana pierwszego redaktora", expected_version=1),
            None,
        )

        with pytest.raises(PersonVersionConflictError):
            await PersonService(stale_session).update_person(
                stale_person,
                PersonUpdateSchema(summary_pl="Zmiana ze starego formularza"),
                None,
            )
        await stale_session.rollback()

    async with session_factory() as verify_session:
        saved = (
            await verify_session.execute(select(Person).where(Person.id == person_id))
        ).scalar_one()
        assert saved.summary_pl == "Zmiana pierwszego redaktora"
        assert saved.version == 2
