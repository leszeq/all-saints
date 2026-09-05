"""Regression coverage for canonical person URLs across soft deletion."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Person


@pytest.mark.asyncio
async def test_soft_deleted_slug_stays_reserved_and_restore_keeps_its_url(
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    original = await service.create_person(
        PersonCreateSchema(canonical_name="Test polityki adresu")
    )

    await service.soft_delete_person(original)
    replacement = await service.create_person(
        PersonCreateSchema(canonical_name="Test polityki adresu")
    )
    restored = await service.restore_person(original.id)

    assert original.slug == "test-polityki-adresu"
    assert replacement.slug == "test-polityki-adresu-1"
    assert restored is not None
    assert restored.slug == original.slug
    assert restored.deleted_at is None

    persisted_slugs = set(
        (
            await db_session.scalars(
                select(Person.slug).where(Person.id.in_([original.id, replacement.id]))
            )
        ).all()
    )
    assert persisted_slugs == {"test-polityki-adresu", "test-polityki-adresu-1"}
