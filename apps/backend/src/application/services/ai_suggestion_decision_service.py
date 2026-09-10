"""Audited editorial decisions for generated AI profile suggestions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai_models import AISuggestionDecisionResult
from src.application.ai_suggestions import tag_list
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_primary_translation_sync import (
    PersonPrimaryTranslationSynchronizer,
)
from src.application.services.person_service import PersonVersionConflictError
from src.application.services.person_snapshot import serialize_person_snapshot
from src.domain.hagiography.models import Person, PersonTag, PersonVersion, Tag
from src.domain.identity.models import AuditAction


class AISuggestionNotFoundError(ValueError):
    """Raised when a person or pending suggestion does not exist."""


class AISuggestionDecisionError(ValueError):
    """Raised when an AI suggestion decision is invalid."""


class AISuggestionDecisionService:
    """Apply an explicit human decision without bypassing person versioning."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def decide(
        self,
        person_id: uuid.UUID,
        *,
        kind: Literal["summary", "tags"],
        action: Literal["accept", "reject"],
        expected_version: int,
        user_id: uuid.UUID | None,
        value: str | None = None,
        selected_tags: list[str] | None = None,
        note: str | None = None,
        audit_context: AuditContext | None = None,
    ) -> AISuggestionDecisionResult:
        """Accept or reject one pending summary or tag proposal."""
        if kind not in {"summary", "tags"}:
            raise AISuggestionDecisionError("Ten typ sugestii nie obsługuje decyzji")
        if action not in {"accept", "reject"}:
            raise AISuggestionDecisionError("Nieznana decyzja redakcyjna")

        normalized_note = note.strip() if note else None
        if action == "reject" and not normalized_note:
            raise AISuggestionDecisionError("Odrzucenie sugestii wymaga uzasadnienia")

        person = (
            await self._db.execute(
                select(Person)
                .where(Person.id == person_id, Person.deleted_at.is_(None))
                .with_for_update()
            )
        ).scalar_one_or_none()
        if person is None:
            raise AISuggestionNotFoundError("Profil osoby nie istnieje")
        if person.version != expected_version:
            raise PersonVersionConflictError(expected_version, person.version)

        previous_snapshot = await serialize_person_snapshot(self._db, person)
        applied_value: str | None = None
        accepted_tags: list[str] = []

        if kind == "summary":
            suggestion = (person.ai_summary or "").strip()
            if not suggestion:
                raise AISuggestionNotFoundError("Brak oczekującego streszczenia AI")
            if action == "accept":
                applied_value = (value or suggestion).strip()
                if not applied_value:
                    raise AISuggestionDecisionError("Zatwierdzone streszczenie nie może być puste")
                person.summary_pl = applied_value
                await PersonPrimaryTranslationSynchronizer(self._db).sync_existing(
                    person,
                    changed_fields={"summary_pl"},
                    user_id=user_id,
                )
            person.ai_summary = None
        else:
            available_tags = tag_list(person.ai_tags)
            if not available_tags:
                raise AISuggestionNotFoundError("Brak oczekujących tagów AI")
            if action == "accept":
                accepted_tags = self._validated_tag_selection(
                    available_tags,
                    selected_tags or available_tags,
                )
                await self._link_tags(person, accepted_tags)
                applied_value = ", ".join(accepted_tags)
            person.ai_tags = None

        decided_at = datetime.now(UTC)
        person.version += 1
        person.updated_at = decided_at
        await self._db.flush()
        current_snapshot = await serialize_person_snapshot(self._db, person)
        change_summary = (
            f"AI: zatwierdzono sugestię {kind}"
            if action == "accept"
            else f"AI: odrzucono sugestię {kind} — {normalized_note}"
        )
        self._db.add(
            PersonVersion(
                person_id=person.id,
                version_number=person.version,
                snapshot=current_snapshot,
                changed_by_id=user_id,
                changed_at=decided_at,
                change_summary=change_summary,
            )
        )
        add_audit_log(
            self._db,
            context=audit_context or AuditContext.for_user(user_id),
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
            extra_metadata={
                "source": "ai_suggestion",
                "kind": kind,
                "decision": action,
                "note": normalized_note,
                "accepted_tags": accepted_tags,
            },
        )
        await self._db.flush()
        return AISuggestionDecisionResult(
            person_id=person.id,
            kind=kind,
            action=action,
            applied_value=applied_value,
            accepted_tags=accepted_tags,
            version=person.version,
            decided_at=decided_at,
        )

    @staticmethod
    def _validated_tag_selection(available: list[str], selected: list[str]) -> list[str]:
        available_by_key = {item.casefold(): item for item in available}
        normalized: list[str] = []
        seen: set[str] = set()
        for item in selected:
            key = item.strip().casefold()
            if not key or key in seen:
                continue
            if key not in available_by_key:
                raise AISuggestionDecisionError(
                    f"Tag „{item.strip()}” nie należy do aktualnej sugestii AI"
                )
            seen.add(key)
            normalized.append(available_by_key[key])
        if not normalized:
            raise AISuggestionDecisionError("Wybierz co najmniej jeden tag do zatwierdzenia")
        return normalized

    async def _link_tags(self, person: Person, names: list[str]) -> None:
        existing_links = set(
            (
                await self._db.execute(
                    select(PersonTag.tag_id).where(PersonTag.person_id == person.id)
                )
            )
            .scalars()
            .all()
        )
        for name in names:
            tag = (
                await self._db.execute(
                    select(Tag).where(
                        Tag.deleted_at.is_(None),
                        func.lower(Tag.name_pl) == name.casefold(),
                    )
                )
            ).scalar_one_or_none()
            if tag is None:
                tag = Tag(
                    name_pl=name,
                    name_en=name,
                    slug=await self._unique_tag_slug(name),
                )
                self._db.add(tag)
                await self._db.flush()
            if tag.id not in existing_links:
                self._db.add(PersonTag(person_id=person.id, tag_id=tag.id))
                existing_links.add(tag.id)

    async def _unique_tag_slug(self, name: str) -> str:
        base = slugify(name) or "tag"
        candidate = base
        suffix = 2
        while (
            await self._db.execute(select(Tag.id).where(Tag.slug == candidate))
        ).scalar_one_or_none() is not None:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate
