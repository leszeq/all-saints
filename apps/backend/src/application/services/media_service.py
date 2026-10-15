"""Application service for image and document metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.media import CreateDocumentCommand, CreateImageCommand
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.pagination import execute_page
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.application.services.published_content_guard import (
    require_published_change_permission,
)
from src.domain.identity.models import AuditAction
from src.domain.sources.models import Document, Image, ImageLicense


class MediaPersonNotFoundError(ValueError):
    """Raised when image metadata references a missing person."""


class MediaService:
    """Read and create media metadata inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_images(
        self,
        *,
        person_id: uuid.UUID | None = None,
        license: ImageLicense | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Image], int]:
        """Return one filtered page of active image metadata."""
        statement = select(Image).where(Image.deleted_at.is_(None))
        if person_id is not None:
            statement = statement.where(Image.person_id == person_id)
        if license is not None:
            statement = statement.where(Image.license == license.value)
        statement = statement.order_by(Image.is_primary.desc(), Image.sort_order.asc())
        return await execute_page(self.db, statement, page=page, per_page=per_page)

    async def create_image(
        self,
        data: CreateImageCommand,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
        allow_published_update: bool = False,
    ) -> Image:
        """Create an image and version its person relation when present."""
        person = None
        previous_snapshot = None
        if data.person_id is not None:
            person = await lock_person_for_snapshot(self.db, data.person_id)
            if person is None:
                raise MediaPersonNotFoundError("Osoba nie istnieje")
            require_published_change_permission(
                person,
                allow_published_update=allow_published_update,
            )
            previous_snapshot = await serialize_person_snapshot(self.db, person)
            if data.is_primary:
                await self.db.execute(
                    update(Image)
                    .where(
                        Image.person_id == data.person_id,
                        Image.deleted_at.is_(None),
                        Image.is_primary.is_(True),
                    )
                    .values(is_primary=False)
                )

        image = Image(**data.model_dump(mode="json"))
        self.db.add(image)
        await self.db.flush()

        if person is not None and previous_snapshot is not None:
            previous_snapshot, current_snapshot = await append_relation_version(
                self.db,
                person,
                previous_snapshot=previous_snapshot,
                changed_by_id=user_id,
                change_summary="Dodanie obrazu",
            )
            add_audit_log(
                self.db,
                context=audit_context or AuditContext.for_user(user_id),
                action=AuditAction.UPDATE,
                resource_type="persons",
                resource_id=person.id,
                old_value=previous_snapshot,
                new_value=current_snapshot,
                extra_metadata={"relation": "images", "operation": "add"},
            )
            await self.db.flush()

        await self.db.refresh(image)
        return image

    async def create_document(self, data: CreateDocumentCommand) -> Document:
        """Create document metadata without crossing the HTTP boundary."""
        document = Document(**data.model_dump(mode="json"))
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def list_documents(
        self,
        *,
        person_id: uuid.UUID | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Document], int]:
        """Return one filtered page of active document metadata."""
        statement = select(Document).where(Document.deleted_at.is_(None))
        if person_id is not None:
            statement = statement.where(Document.person_id == person_id)
        statement = statement.order_by(Document.created_at.desc())
        return await execute_page(self.db, statement, page=page, per_page=per_page)
