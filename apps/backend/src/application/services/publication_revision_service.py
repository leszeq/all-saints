"""Create isolated editorial drafts for published person profiles."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_service import PersonVersionConflictError
from src.application.services.person_snapshot import (
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.hagiography.models import PublicationRevision, PublicationRevisionStatus
from src.domain.identity.models import AuditAction

__all__ = [
    "PublicationRevisionConflictError",
    "PublicationRevisionNotFoundError",
    "PublicationRevisionService",
    "PublicationRevisionStateError",
]


class PublicationRevisionNotFoundError(ValueError):
    """Raised when the requested person or revision does not exist."""


class PublicationRevisionConflictError(ValueError):
    """Raised when a person already has an active draft revision."""


class PublicationRevisionStateError(ValueError):
    """Raised when a revision cannot be created for the current person state."""


class PublicationRevisionService:
    """Persist revision snapshots without mutating the live person record."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_draft(
        self,
        person_id: uuid.UUID,
        *,
        expected_version: int,
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
        change_summary: str | None = None,
    ) -> PublicationRevision:
        """Create one draft from the current published person version."""
        person = await lock_person_for_snapshot(self.db, person_id)
        if person is None:
            raise PublicationRevisionNotFoundError("Osoba nie istnieje")
        if person.version != expected_version:
            raise PersonVersionConflictError(expected_version, person.version)
        status_value = person.status.value if hasattr(person.status, "value") else str(person.status)
        if status_value != "published":
            raise PublicationRevisionStateError(
                "Izolowaną rewizję można rozpocząć tylko dla opublikowanego profilu"
            )

        active_draft = await self.db.scalar(
            select(PublicationRevision).where(
                PublicationRevision.person_id == person.id,
                PublicationRevision.status == PublicationRevisionStatus.DRAFT.value,
                PublicationRevision.deleted_at.is_(None),
            )
        )
        if active_draft is not None:
            raise PublicationRevisionConflictError(
                "Profil ma już otwartą rewizję w stanie draft"
            )

        last_number = await self.db.scalar(
            select(func.max(PublicationRevision.revision_number)).where(
                PublicationRevision.person_id == person.id,
            )
        )
        revision = PublicationRevision(
            person_id=person.id,
            revision_number=int(last_number or 0) + 1,
            status=PublicationRevisionStatus.DRAFT.value,
            base_version=person.version,
            payload=await serialize_person_snapshot(self.db, person),
            author_id=author_id,
            change_summary=change_summary.strip() if change_summary else None,
        )
        self.db.add(revision)
        await self.db.flush()
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(author_id),
            action=AuditAction.CREATE,
            resource_type="person_revisions",
            resource_id=revision.id,
            new_value={
                "person_id": str(person.id),
                "revision_number": revision.revision_number,
                "base_version": revision.base_version,
                "status": revision.status,
            },
            extra_metadata={"operation": "create_person_revision"},
        )
        await self.db.flush()
        await self.db.refresh(revision)
        return revision
