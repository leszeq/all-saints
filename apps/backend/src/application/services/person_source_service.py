"""Application service for versioned person-to-source assignments."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.commands.person_sources import (
    CreatePersonSourceCommand,
    CreatePersonWebSourceCommand,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.hagiography.models import Person
from src.domain.identity.models import AuditAction
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    PersonSource,
    SourceType,
)


class PersonSourceNotFoundError(ValueError):
    """Raised when a person, source, or assignment cannot be found."""


class PersonSourceConflictError(ValueError):
    """Raised when a source is already assigned to the person."""


class PersonSourceService:
    """Read and mutate source assignments inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_sources(self, person_id: uuid.UUID) -> list[PersonSource]:
        """Return active bibliography and historical-source assignments."""
        result = await self.db.execute(
            select(PersonSource)
            .options(
                selectinload(PersonSource.bibliography),
                selectinload(PersonSource.historical_source),
            )
            .where(
                PersonSource.person_id == person_id,
                PersonSource.deleted_at.is_(None),
                or_(
                    PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
                    PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
                ),
            )
            .order_by(PersonSource.is_primary.desc(), PersonSource.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_source(
        self,
        person_id: uuid.UUID,
        data: CreatePersonSourceCommand,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
    ) -> PersonSource:
        """Create a non-duplicated source assignment with a person snapshot."""
        person = await self._person_for_change(person_id)
        previous_snapshot = await serialize_person_snapshot(self.db, person)

        source_model = Bibliography if data.bibliography_id is not None else HistoricalSource
        source_id = data.bibliography_id or data.historical_source_id
        source = (
            await self.db.execute(
                select(source_model).where(
                    source_model.id == source_id,
                    source_model.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if source is None:
            raise PersonSourceNotFoundError("Źródło nie istnieje")

        source_field = (
            PersonSource.bibliography_id
            if data.bibliography_id is not None
            else PersonSource.historical_source_id
        )
        existing = (
            await self.db.execute(
                select(PersonSource).where(
                    PersonSource.person_id == person_id,
                    source_field == source_id,
                    PersonSource.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise PersonSourceConflictError("To źródło jest już przypisane do postaci")

        link = PersonSource(person_id=person_id, **data.model_dump())
        self.db.add(link)
        await self.db.flush()
        await self._record_change(
            person,
            previous_snapshot,
            user_id=user_id,
            audit_context=audit_context,
            change_summary="Dodanie źródła",
            operation="add",
        )
        return await self._get_loaded_link(link.id)

    async def create_web_source(
        self,
        person_id: uuid.UUID,
        data: CreatePersonWebSourceCommand,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
    ) -> PersonSource:
        """Create or reuse a URL source and attach it in one transaction."""
        person = await self._person_for_change(person_id)
        previous_snapshot = await serialize_person_snapshot(self.db, person)

        normalized_url = str(data.url)
        bibliography = (
            await self.db.execute(
                select(Bibliography).where(
                    Bibliography.url == normalized_url,
                    Bibliography.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if bibliography is None:
            bibliography = Bibliography(
                source_type=SourceType.WEBSITE,
                title=data.title,
                url=normalized_url,
                authors=data.authors,
                publisher=data.publisher,
                year=data.year,
                language=data.language,
                reliability_score=data.reliability_score,
            )
            self.db.add(bibliography)
            await self.db.flush()

        existing = (
            await self.db.execute(
                select(PersonSource).where(
                    PersonSource.person_id == person_id,
                    PersonSource.bibliography_id == bibliography.id,
                    PersonSource.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise PersonSourceConflictError("Ten link jest już przypisany do postaci")

        link = PersonSource(
            person_id=person_id,
            bibliography_id=bibliography.id,
            page_reference=data.page_reference,
            relevance_score=data.relevance_score,
            is_primary=data.is_primary,
            notes=data.notes,
        )
        self.db.add(link)
        await self.db.flush()
        await self._record_change(
            person,
            previous_snapshot,
            user_id=user_id,
            audit_context=audit_context,
            change_summary="Dodanie źródła internetowego",
            operation="add",
        )
        return await self._get_loaded_link(link.id)

    async def delete_source(
        self,
        person_id: uuid.UUID,
        link_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
    ) -> None:
        """Soft-delete one assignment without deleting the source itself."""
        person = await self._person_for_change(person_id)
        link = (
            await self.db.execute(
                select(PersonSource).where(
                    PersonSource.id == link_id,
                    PersonSource.person_id == person_id,
                    PersonSource.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if link is None:
            raise PersonSourceNotFoundError("Przypisanie źródła nie istnieje")

        previous_snapshot = await serialize_person_snapshot(self.db, person)
        link.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await self._record_change(
            person,
            previous_snapshot,
            user_id=user_id,
            audit_context=audit_context,
            change_summary="Usunięcie źródła",
            operation="remove",
        )

    async def _person_for_change(self, person_id: uuid.UUID) -> Person:
        person = await lock_person_for_snapshot(self.db, person_id)
        if person is None:
            raise PersonSourceNotFoundError("Osoba nie istnieje")
        return person

    async def _get_loaded_link(self, link_id: uuid.UUID) -> PersonSource:
        result = await self.db.execute(
            select(PersonSource)
            .options(
                selectinload(PersonSource.bibliography),
                selectinload(PersonSource.historical_source),
            )
            .where(PersonSource.id == link_id)
        )
        return result.scalar_one()

    async def _record_change(
        self,
        person: Person,
        previous_snapshot: dict[str, object],
        *,
        user_id: uuid.UUID | None,
        audit_context: AuditContext | None,
        change_summary: str,
        operation: str,
    ) -> None:
        previous_snapshot, current_snapshot = await append_relation_version(
            self.db,
            person,
            previous_snapshot=previous_snapshot,
            changed_by_id=user_id,
            change_summary=change_summary,
        )
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(user_id),
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
            extra_metadata={"relation": "sources", "operation": operation},
        )
        await self.db.flush()
