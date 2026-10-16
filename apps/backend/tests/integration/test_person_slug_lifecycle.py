"""Regression coverage for canonical person URLs across soft deletion."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema, PersonUpdateSchema
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Person, PublicationStatus


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


@pytest.mark.asyncio
async def test_renamed_published_person_keeps_a_permanent_slug_redirect(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    person = await service.create_person(PersonCreateSchema(canonical_name="Św. Stary Adres"))
    person.status = PublicationStatus.PUBLISHED.value
    await db_session.commit()
    await db_session.refresh(person)
    old_slug = person.slug

    await service.update_person(
        person,
        PersonUpdateSchema(
            canonical_name="Św. Nowy Adres",
            expected_version=person.version,
        ),
    )
    await db_session.commit()
    new_slug = person.slug

    response = await async_client.get(
        f"/api/v1/persons/{old_slug}",
        follow_redirects=False,
    )

    assert response.status_code == 301
    assert response.headers["location"].endswith(f"/api/v1/persons/{new_slug}")


@pytest.mark.asyncio
async def test_public_person_index_is_published_only_and_cursor_paginated(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    service = PersonService(db_session)
    first = await service.create_person(PersonCreateSchema(canonical_name="Św. Indeks Pierwszy"))
    second = await service.create_person(PersonCreateSchema(canonical_name="Św. Indeks Drugi"))
    draft = await service.create_person(PersonCreateSchema(canonical_name="Szkic Poza Indeksem"))
    for person in (first, second):
        person.status = PublicationStatus.PUBLISHED.value
    draft.deleted_at = datetime.now(UTC)
    await db_session.commit()

    first_page = await async_client.get("/api/v1/public-index/persons", params={"limit": 1})
    assert first_page.status_code == 200
    first_data = first_page.json()
    assert len(first_data["items"]) == 1
    assert first_data["next_cursor"]

    second_page = await async_client.get(
        "/api/v1/public-index/persons",
        params={"limit": 1, "cursor": first_data["next_cursor"]},
    )
    assert second_page.status_code == 200
    second_data = second_page.json()
    assert len(second_data["items"]) == 1
    assert {first_data["items"][0]["slug"], second_data["items"][0]["slug"]} == {
        first.slug,
        second.slug,
    }
    assert second_data["next_cursor"] is None

    invalid = await async_client.get(
        "/api/v1/public-index/persons",
        params={"cursor": "not-a-valid-cursor"},
    )
    assert invalid.status_code == 400
