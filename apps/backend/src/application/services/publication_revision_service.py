"""Create isolated editorial drafts for published person profiles."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonUpdateSchema
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_service import PersonService, PersonVersionConflictError
from src.application.services.person_snapshot import (
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.hagiography.models import (
    PublicationRevision,
    PublicationRevisionStatus,
    PublicationStatus,
)
from src.domain.identity.models import AuditAction

__all__ = [
    "PublicationRevisionConflictError",
    "PublicationRevisionNotFoundError",
    "PublicationRevisionPayloadError",
    "PublicationRevisionService",
    "PublicationRevisionStateError",
    "PublicationRevisionVersionConflictError",
]


REVISION_EDITABLE_FIELDS = frozenset(
    {
        "person_type",
        "canonical_name",
        "canonical_name_en",
        "latin_name",
        "original_name",
        "surnames",
        "religious_name",
        "epithets",
        "gender",
        "era",
        "century",
        "birth_date",
        "birth_year",
        "death_date",
        "death_year",
        "birth_place_id",
        "death_place_id",
        "birth_country_id",
        "death_country_id",
        "nationality_id",
        "state_of_life_id",
        "summary_pl",
        "biography_pl",
        "summary_en",
        "biography_en",
        "iconographic_attributes",
        "prayers",
        "works",
        "liturgical_color",
        "is_featured",
        "external_ids",
    }
)

REVISION_WORKFLOW_FIELDS = frozenset(
    {
        "status",
        "change_summary",
        "expected_version",
        "id",
        "slug",
        "created_at",
        "updated_at",
        "deleted_at",
        "version",
        "search_vector",
        "sort_name",
        "_snapshot_schema_version",
    }
)


class PublicationRevisionNotFoundError(ValueError):
    """Raised when the requested person or revision does not exist."""


class PublicationRevisionConflictError(ValueError):
    """Raised when a person already has an active draft revision."""


class PublicationRevisionStateError(ValueError):
    """Raised when a revision operation is invalid for the current workflow state."""


class PublicationRevisionVersionConflictError(RuntimeError):
    """Raised when an editor patches a stale revision snapshot."""

    def __init__(self, expected_version: int, current_version: int) -> None:
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"Rewizja ma już wersję {current_version}, a formularz wersję "
            f"{expected_version}. Odśwież rewizję i ponów zmiany."
        )


class PublicationRevisionPayloadError(ValueError):
    """Raised when a revision patch contains unsupported or invalid fields."""

    def __init__(self, details: list[dict[str, str]]) -> None:
        self.details = details
        super().__init__("Dane rewizji zawierają błędy walidacji")


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

    async def update_draft(
        self,
        revision_id: uuid.UUID,
        *,
        expected_version: int,
        changes: dict[str, Any],
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
        change_summary: str | None = None,
    ) -> PublicationRevision:
        """Merge validated scalar profile changes into a draft snapshot."""
        revision = await self.db.scalar(
            select(PublicationRevision)
            .where(
                PublicationRevision.id == revision_id,
                PublicationRevision.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if revision is None:
            raise PublicationRevisionNotFoundError("Rewizja nie istnieje")
        if revision.version != expected_version:
            raise PublicationRevisionVersionConflictError(expected_version, revision.version)
        if revision.status != PublicationRevisionStatus.DRAFT.value:
            raise PublicationRevisionStateError(
                "Edycja jest możliwa wyłącznie dla rewizji w stanie draft"
            )

        forbidden_fields = sorted(set(changes) & REVISION_WORKFLOW_FIELDS)
        unknown_fields = sorted(set(changes) - REVISION_EDITABLE_FIELDS - REVISION_WORKFLOW_FIELDS)
        if forbidden_fields or unknown_fields:
            details = [
                {
                    "field": f"changes.{field}",
                    "message": "Pole jest zarządzane przez workflow rewizji",
                    "type": "revision_field_forbidden",
                }
                for field in forbidden_fields
            ] + [
                {
                    "field": f"changes.{field}",
                    "message": "Pole nie jest obsługiwane w tym etapie edycji rewizji",
                    "type": "extra_forbidden",
                }
                for field in unknown_fields
            ]
            raise PublicationRevisionPayloadError(details)

        try:
            validated = PersonUpdateSchema.model_validate(changes)
        except ValidationError as exc:
            details = [
                {
                    "field": "changes." + ".".join(str(part) for part in error["loc"]),
                    "message": str(error["msg"]),
                    "type": str(error["type"]),
                }
                for error in exc.errors()
            ]
            raise PublicationRevisionPayloadError(details) from exc

        normalized_changes = validated.model_dump(mode="json", exclude_unset=True)
        if not normalized_changes:
            raise PublicationRevisionPayloadError(
                [
                    {
                        "field": "changes",
                        "message": "Podaj co najmniej jedno pole do zmiany",
                        "type": "empty_patch",
                    }
                ]
            )

        previous_version = revision.version
        previous_payload = dict(revision.payload)
        revision.payload = {**previous_payload, **jsonable_encoder(normalized_changes)}
        revision.version = previous_version + 1
        revision.updated_at = datetime.now(UTC)
        if change_summary is not None:
            revision.change_summary = change_summary.strip() or None

        await self.db.flush()
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(author_id),
            action=AuditAction.UPDATE,
            resource_type="person_revisions",
            resource_id=revision.id,
            old_value={
                "version": previous_version,
                "changes": {field: previous_payload.get(field) for field in normalized_changes},
            },
            new_value={
                "version": revision.version,
                "changes": jsonable_encoder(normalized_changes),
            },
            extra_metadata={"operation": "update_person_revision"},
        )
        await self.db.flush()
        await self.db.refresh(revision)
        return revision

    async def submit_for_review(
        self,
        revision_id: uuid.UUID,
        *,
        expected_version: int,
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
        note: str | None = None,
    ) -> PublicationRevision:
        """Move a draft revision to review without touching the live person."""
        revision = await self.db.scalar(
            select(PublicationRevision)
            .where(
                PublicationRevision.id == revision_id,
                PublicationRevision.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if revision is None:
            raise PublicationRevisionNotFoundError("Rewizja nie istnieje")
        if revision.version != expected_version:
            raise PublicationRevisionVersionConflictError(expected_version, revision.version)
        if revision.status != PublicationRevisionStatus.DRAFT.value:
            raise PublicationRevisionStateError(
                "Do recenzji można przekazać wyłącznie rewizję w stanie draft"
            )

        previous_version = revision.version
        previous_status = revision.status
        revision.status = PublicationRevisionStatus.REVIEW.value
        revision.version = previous_version + 1
        revision.updated_at = datetime.now(UTC)
        if note is not None:
            revision.change_summary = note.strip() or None

        await self.db.flush()
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(author_id),
            action=AuditAction.UPDATE,
            resource_type="person_revisions",
            resource_id=revision.id,
            old_value={"status": previous_status, "version": previous_version},
            new_value={"status": revision.status, "version": revision.version},
            extra_metadata={"operation": "submit_person_revision"},
        )
        await self.db.flush()
        await self.db.refresh(revision)
        return revision

    async def return_to_draft(
        self,
        revision_id: uuid.UUID,
        *,
        expected_version: int,
        note: str,
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
    ) -> PublicationRevision:
        """Return a reviewed revision to the editor with a required note."""
        return await self._review_decision(
            revision_id,
            expected_version=expected_version,
            target_status=PublicationRevisionStatus.DRAFT,
            note=note,
            author_id=author_id,
            audit_context=audit_context,
        )

    async def reject(
        self,
        revision_id: uuid.UUID,
        *,
        expected_version: int,
        note: str,
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
    ) -> PublicationRevision:
        """Reject a reviewed revision while retaining its immutable history."""
        return await self._review_decision(
            revision_id,
            expected_version=expected_version,
            target_status=PublicationRevisionStatus.REJECTED,
            note=note,
            author_id=author_id,
            audit_context=audit_context,
        )

    async def _review_decision(
        self,
        revision_id: uuid.UUID,
        *,
        expected_version: int,
        target_status: PublicationRevisionStatus,
        note: str,
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
    ) -> PublicationRevision:
        """Persist one reviewer decision from the review state."""
        revision = await self.db.scalar(
            select(PublicationRevision)
            .where(
                PublicationRevision.id == revision_id,
                PublicationRevision.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if revision is None:
            raise PublicationRevisionNotFoundError("Rewizja nie istnieje")
        if revision.version != expected_version:
            raise PublicationRevisionVersionConflictError(expected_version, revision.version)
        if revision.status != PublicationRevisionStatus.REVIEW.value:
            raise PublicationRevisionStateError(
                "Decyzja recenzenta wymaga rewizji w stanie review"
            )
        normalized_note = note.strip()
        if not normalized_note:
            raise PublicationRevisionPayloadError(
                [
                    {
                        "field": "note",
                        "message": "Komentarz recenzenta nie może być pusty",
                        "type": "required",
                    }
                ]
            )

        previous_version = revision.version
        previous_status = revision.status
        revision.status = target_status.value
        revision.version = previous_version + 1
        revision.updated_at = datetime.now(UTC)
        revision.change_summary = normalized_note

        await self.db.flush()
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(author_id),
            action=AuditAction.UPDATE,
            resource_type="person_revisions",
            resource_id=revision.id,
            old_value={"status": previous_status, "version": previous_version},
            new_value={
                "status": revision.status,
                "version": revision.version,
                "note": normalized_note,
            },
            extra_metadata={"operation": f"{target_status.value}_person_revision"},
        )
        await self.db.flush()
        await self.db.refresh(revision)
        return revision

    async def publish(
        self,
        revision_id: uuid.UUID,
        *,
        expected_version: int,
        author_id: uuid.UUID | None,
        audit_context: AuditContext | None = None,
        note: str | None = None,
    ) -> PublicationRevision:
        """Publish a reviewed revision atomically into the live person row."""
        revision = await self.db.scalar(
            select(PublicationRevision)
            .where(
                PublicationRevision.id == revision_id,
                PublicationRevision.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if revision is None:
            raise PublicationRevisionNotFoundError("Rewizja nie istnieje")
        if revision.version != expected_version:
            raise PublicationRevisionVersionConflictError(expected_version, revision.version)
        if revision.status != PublicationRevisionStatus.REVIEW.value:
            raise PublicationRevisionStateError(
                "Opublikować można wyłącznie rewizję oczekującą na recenzję"
            )

        person = await lock_person_for_snapshot(self.db, revision.person_id)
        if person is None:
            raise PublicationRevisionNotFoundError("Osoba dla rewizji nie istnieje")
        if person.version != revision.base_version:
            raise PersonVersionConflictError(revision.base_version, person.version)
        person_status = person.status.value if hasattr(person.status, "value") else str(person.status)
        if person_status != PublicationStatus.PUBLISHED.value:
            raise PublicationRevisionStateError(
                "Rewizję można opublikować tylko dla nadal opublikowanego profilu"
            )

        publish_summary = note.strip() if note else None
        if not publish_summary:
            publish_summary = revision.change_summary or f"Publikacja rewizji #{revision.revision_number}"
        person_update = self._person_update_from_payload(
            revision.payload,
            expected_version=person.version,
            change_summary=publish_summary,
        )
        await PersonService(self.db).update_person(
            person,
            person_update,
            user_id=author_id,
            allow_status_change=True,
            allow_published_update=True,
            audit_context=audit_context,
        )
        # Keep the selected public revision on the live row in the same
        # transaction as the scalar projection. Legacy direct edits clear this
        # pointer in ``PersonService`` before this assignment, so a successful
        # revision publish always leaves an explicit projection target.
        person.published_revision_id = revision.id
        person.updated_at = datetime.now(UTC)
        await self.db.flush()

        previous_version = revision.version
        previous_status = revision.status
        revision.status = PublicationRevisionStatus.PUBLISHED.value
        revision.version = previous_version + 1
        revision.updated_at = datetime.now(UTC)
        if note is not None:
            revision.change_summary = note.strip() or None

        await self.db.flush()
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(author_id),
            action=AuditAction.PUBLISH,
            resource_type="person_revisions",
            resource_id=revision.id,
            old_value={"status": previous_status, "version": previous_version},
            new_value={
                "status": revision.status,
                "version": revision.version,
                "person_version": person.version,
            },
            extra_metadata={"operation": "publish_person_revision"},
        )
        await self.db.flush()
        await self.db.refresh(revision)
        return revision

    @staticmethod
    def _person_update_from_payload(
        payload: dict[str, Any],
        *,
        expected_version: int,
        change_summary: str,
    ) -> PersonUpdateSchema:
        """Convert a revision snapshot into a safe scalar person update."""
        editable_payload = {
            field: payload[field] for field in REVISION_EDITABLE_FIELDS if field in payload
        }
        editable_payload.update(
            {
                "status": PublicationStatus.PUBLISHED.value,
                "expected_version": expected_version,
                "change_summary": change_summary,
            }
        )
        try:
            return PersonUpdateSchema.model_validate(editable_payload)
        except ValidationError as exc:
            details = [
                {
                    "field": "payload." + ".".join(str(part) for part in error["loc"]),
                    "message": str(error["msg"]),
                    "type": str(error["type"]),
                }
                for error in exc.errors()
            ]
            raise PublicationRevisionPayloadError(details) from exc
