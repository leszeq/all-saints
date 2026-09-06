"""Application service for versioned and audited person translations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.person_translations import (
    TRANSLATED_CONTENT_FIELDS,
    CreatePersonTranslationCommand,
    UpdatePersonTranslationCommand,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_localization import normalize_content_locale
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.hagiography.models import Person, PersonTranslation, PublicationStatus
from src.domain.identity.models import AuditAction


class PersonTranslationNotFoundError(LookupError):
    """Raised when the parent person or requested translation does not exist."""


class PersonTranslationConflictError(RuntimeError):
    """Raised when an active translation already occupies a locale."""


class PersonTranslationStateError(RuntimeError):
    """Raised when translated content is changed outside the draft stage."""


class PersonTranslationContentError(ValueError):
    """Raised when an update would leave a translation without any content."""


class PersonTranslationVersionConflictError(RuntimeError):
    """Raised for an optimistic-lock mismatch on a person or translation."""

    def __init__(self, *, resource: str, expected_version: int, current_version: int) -> None:
        self.resource = resource
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"Rekord {resource} ma już wersję {current_version}, a formularz wersję "
            f"{expected_version}. Odśwież dane i ponów zmianę."
        )


@dataclass(frozen=True, slots=True)
class PersonTranslationListResult:
    """Active translations together with the parent editorial revision."""

    items: list[PersonTranslation]
    person_version: int
    person_status: str


@dataclass(frozen=True, slots=True)
class PersonTranslationMutationResult:
    """Mutated translation and the new revision of its parent person."""

    translation: PersonTranslation
    person_version: int
    operation: str


class PersonTranslationService:
    """Keep translation changes inside the person's editorial boundary."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _require_version(*, resource: str, expected: int, current: int) -> None:
        if expected != current:
            raise PersonTranslationVersionConflictError(
                resource=resource,
                expected_version=expected,
                current_version=current,
            )

    @staticmethod
    def _require_draft(person: Person) -> None:
        status_value = (
            person.status.value if hasattr(person.status, "value") else str(person.status)
        )
        if status_value != PublicationStatus.DRAFT.value:
            raise PersonTranslationStateError(
                "Tłumaczenia można zmieniać tylko wtedy, gdy rekord osoby jest szkicem"
            )

    async def _active_person(self, person_id: uuid.UUID) -> Person:
        person = (
            await self.db.execute(
                select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if person is None:
            raise PersonTranslationNotFoundError("Osoba nie istnieje")
        return person

    async def _translation(
        self,
        person_id: uuid.UUID,
        language_code: str,
        *,
        active_only: bool,
        lock: bool = False,
    ) -> PersonTranslation | None:
        query = select(PersonTranslation).where(
            PersonTranslation.person_id == person_id,
            PersonTranslation.language_code == normalize_content_locale(language_code),
        )
        if active_only:
            query = query.where(PersonTranslation.deleted_at.is_(None))
        if lock:
            query = query.with_for_update()
        return (await self.db.execute(query)).scalar_one_or_none()

    async def list_active(self, person_id: uuid.UUID) -> PersonTranslationListResult:
        """List active translations for any visible editorial state."""
        person = await self._active_person(person_id)
        translations = list(
            (
                await self.db.execute(
                    select(PersonTranslation)
                    .where(
                        PersonTranslation.person_id == person_id,
                        PersonTranslation.deleted_at.is_(None),
                    )
                    .order_by(PersonTranslation.language_code.asc())
                )
            )
            .scalars()
            .all()
        )
        status_value = (
            person.status.value if hasattr(person.status, "value") else str(person.status)
        )
        return PersonTranslationListResult(
            items=translations,
            person_version=person.version,
            person_status=status_value,
        )

    async def _locked_draft(self, person_id: uuid.UUID, expected_version: int) -> Person:
        person = await lock_person_for_snapshot(self.db, person_id)
        if person is None:
            raise PersonTranslationNotFoundError("Osoba nie istnieje")
        self._require_version(
            resource="person",
            expected=expected_version,
            current=person.version,
        )
        self._require_draft(person)
        return person

    @staticmethod
    def _content_after_update(
        translation: PersonTranslation,
        command: UpdatePersonTranslationCommand,
    ) -> dict[str, str | None]:
        values = {field: getattr(translation, field) for field in TRANSLATED_CONTENT_FIELDS}
        for field in command.model_fields_set.intersection(TRANSLATED_CONTENT_FIELDS):
            values[field] = getattr(command, field)
        if not any(values.values()):
            raise PersonTranslationContentError(
                "Tłumaczenie musi zawierać co najmniej jedno pole treści"
            )
        return values

    async def _finish_mutation(
        self,
        *,
        person: Person,
        translation: PersonTranslation,
        previous_snapshot: dict[str, object],
        user_id: uuid.UUID,
        audit_context: AuditContext,
        operation: str,
        change_summary: str,
    ) -> PersonTranslationMutationResult:
        old_snapshot, current_snapshot = await append_relation_version(
            self.db,
            person,
            previous_snapshot=previous_snapshot,
            changed_by_id=user_id,
            change_summary=change_summary,
        )
        add_audit_log(
            self.db,
            context=audit_context,
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=old_snapshot,
            new_value=current_snapshot,
            extra_metadata={
                "relation": "translations",
                "operation": operation,
                "translation_id": str(translation.id),
                "language_code": translation.language_code,
            },
        )
        await self.db.flush()
        await self.db.refresh(translation)
        return PersonTranslationMutationResult(
            translation=translation,
            person_version=person.version,
            operation=operation,
        )

    async def create(
        self,
        person_id: uuid.UUID,
        command: CreatePersonTranslationCommand,
        *,
        user_id: uuid.UUID,
        audit_context: AuditContext,
    ) -> PersonTranslationMutationResult:
        """Create a locale or restore its soft-deleted row."""
        person = await self._locked_draft(person_id, command.expected_person_version)
        previous_snapshot = await serialize_person_snapshot(self.db, person)
        translation = await self._translation(
            person_id,
            command.language_code,
            active_only=False,
            lock=True,
        )
        operation = "create"
        if translation is not None and translation.deleted_at is None:
            raise PersonTranslationConflictError(
                f"Aktywne tłumaczenie dla języka {command.language_code} już istnieje"
            )

        content = command.model_dump(
            include=set(TRANSLATED_CONTENT_FIELDS),
        )
        if translation is None:
            translation = PersonTranslation(
                person_id=person_id,
                language_code=command.language_code,
                translated_by_id=user_id,
                **content,
            )
            self.db.add(translation)
        else:
            operation = "restore"
            for field, value in content.items():
                setattr(translation, field, value)
            translation.deleted_at = None
            translation.translated_by_id = user_id
            translation.version += 1
            translation.updated_at = datetime.now(UTC)

        await self.db.flush()
        verb = "Przywrócenie" if operation == "restore" else "Utworzenie"
        return await self._finish_mutation(
            person=person,
            translation=translation,
            previous_snapshot=previous_snapshot,
            user_id=user_id,
            audit_context=audit_context,
            operation=operation,
            change_summary=f"{verb} tłumaczenia ({command.language_code})",
        )

    async def update(
        self,
        person_id: uuid.UUID,
        language_code: str,
        command: UpdatePersonTranslationCommand,
        *,
        user_id: uuid.UUID,
        audit_context: AuditContext,
    ) -> PersonTranslationMutationResult:
        """Patch one active translation using optimistic locking."""
        person = await self._locked_draft(person_id, command.expected_person_version)
        translation = await self._translation(
            person_id,
            language_code,
            active_only=True,
            lock=True,
        )
        if translation is None:
            raise PersonTranslationNotFoundError("Tłumaczenie nie istnieje")
        self._require_version(
            resource="translation",
            expected=command.expected_version,
            current=translation.version,
        )
        values = self._content_after_update(translation, command)
        previous_snapshot = await serialize_person_snapshot(self.db, person)
        for field, value in values.items():
            setattr(translation, field, value)
        translation.translated_by_id = user_id
        translation.version += 1
        translation.updated_at = datetime.now(UTC)
        await self.db.flush()
        return await self._finish_mutation(
            person=person,
            translation=translation,
            previous_snapshot=previous_snapshot,
            user_id=user_id,
            audit_context=audit_context,
            operation="update",
            change_summary=f"Aktualizacja tłumaczenia ({translation.language_code})",
        )

    async def delete(
        self,
        person_id: uuid.UUID,
        language_code: str,
        *,
        expected_person_version: int,
        expected_version: int,
        user_id: uuid.UUID,
        audit_context: AuditContext,
    ) -> PersonTranslationMutationResult:
        """Soft-delete one active translation while retaining its history."""
        person = await self._locked_draft(person_id, expected_person_version)
        translation = await self._translation(
            person_id,
            language_code,
            active_only=True,
            lock=True,
        )
        if translation is None:
            raise PersonTranslationNotFoundError("Tłumaczenie nie istnieje")
        self._require_version(
            resource="translation",
            expected=expected_version,
            current=translation.version,
        )
        previous_snapshot = await serialize_person_snapshot(self.db, person)
        translation.deleted_at = datetime.now(UTC)
        translation.translated_by_id = user_id
        translation.version += 1
        translation.updated_at = datetime.now(UTC)
        await self.db.flush()
        return await self._finish_mutation(
            person=person,
            translation=translation,
            previous_snapshot=previous_snapshot,
            user_id=user_id,
            audit_context=audit_context,
            operation="delete",
            change_summary=f"Usunięcie tłumaczenia ({translation.language_code})",
        )
