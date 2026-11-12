"""Integration coverage for isolated publication revision drafts."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.services.audit_service import AuditContext
from src.application.services.person_service import PersonService, PersonVersionConflictError
from src.application.services.publication_revision_service import (
    PublicationRevisionConflictError,
    PublicationRevisionService,
    PublicationRevisionStateError,
)
from src.domain.hagiography.models import (
    Person,
    PublicationRevision,
    PublicationRevisionStatus,
    PublicationStatus,
)
from src.domain.identity.models import AuditLog


async def _published_person(db_session: AsyncSession) -> Person:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Rewizja Testowa",
            summary_pl="Aktualny opis publiczny",
            person_type="saint",
            gender="male",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    await db_session.flush()
    await db_session.refresh(person)
    return person


@pytest.mark.asyncio
async def test_create_draft_revision_keeps_live_person_unchanged(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    base_version = person.version

    revision = await PublicationRevisionService(db_session).create_draft(
        person.id,
        expected_version=base_version,
        author_id=None,
        audit_context=AuditContext(),
        change_summary="Przygotowanie aktualizacji biogramu",
    )

    assert revision.revision_number == 1
    assert revision.status == PublicationRevisionStatus.DRAFT.value
    assert revision.base_version == base_version
    assert revision.change_summary == "Przygotowanie aktualizacji biogramu"
    assert revision.payload["canonical_name"] == person.canonical_name
    assert revision.payload["summary_pl"] == "Aktualny opis publiczny"
    assert person.version == base_version
    assert person.summary_pl == "Aktualny opis publiczny"

    audit_log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.resource_type == "person_revisions",
            AuditLog.resource_id == revision.id,
        )
    )
    assert audit_log is not None
    assert audit_log.new_value == {
        "person_id": str(person.id),
        "revision_number": 1,
        "base_version": base_version,
        "status": PublicationRevisionStatus.DRAFT.value,
    }


@pytest.mark.asyncio
async def test_create_draft_revision_rejects_stale_version_and_duplicate_draft(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )

    with pytest.raises(PersonVersionConflictError):
        await service.create_draft(
            person.id,
            expected_version=person.version - 1,
            author_id=None,
        )

    with pytest.raises(PublicationRevisionConflictError):
        await service.create_draft(
            person.id,
            expected_version=person.version,
            author_id=None,
        )

    assert (
        await db_session.scalar(
            select(PublicationRevision).where(PublicationRevision.person_id == person.id)
        )
    ) is not None


@pytest.mark.asyncio
async def test_create_draft_revision_requires_published_person(
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Szkic bez rewizji",
            person_type="saint",
            gender="male",
        )
    )

    with pytest.raises(PublicationRevisionStateError):
        await PublicationRevisionService(db_session).create_draft(
            person.id,
            expected_version=person.version,
            author_id=None,
        )
