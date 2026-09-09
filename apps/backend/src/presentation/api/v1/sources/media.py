"""Image upload, image catalogue, and document endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import add_audit_log
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.identity.models import AuditAction, User
from src.domain.sources.models import Document, Image, ImageLicense
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
    execute_page,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.image_files import (
    get_uploaded_image,
    upload_avatar_image,
)
from src.presentation.api.v1.sources.image_files import router as image_files_router
from src.presentation.api.v1.sources.schemas import (
    DocumentCreateSchema,
    DocumentSchema,
    ImageCreateSchema,
    ImageSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()

__all__ = ["get_uploaded_image", "upload_avatar_image"]

router.include_router(image_files_router)


@router.get(
    "/images",
    response_model=list[ImageSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List images",
)
async def list_images(
    response: Response,
    person_id: uuid.UUID | None = None,
    license: ImageLicense | None = Query(None),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    limit: Annotated[int | None, Query(ge=1, le=500, deprecated=True)] = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("images", "read")),
) -> list[ImageSchema]:
    query = select(Image).where(Image.deleted_at.is_(None))
    if person_id:
        query = query.where(Image.person_id == person_id)
    if license is not None:
        query = query.where(Image.license == license.value)
    query = query.order_by(Image.is_primary.desc(), Image.sort_order.asc())
    effective_per_page = limit if limit is not None else per_page
    items, total = await execute_page(db, query, page=page, per_page=effective_per_page)
    add_pagination_headers(
        response,
        total=total,
        page=page,
        per_page=effective_per_page,
    )
    return [ImageSchema.model_validate(item) for item in items]


@router.post(
    "/images",
    response_model=ImageSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create image record",
)
async def create_image(
    data: ImageCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("images", "create")),
) -> ImageSchema:
    person = None
    previous_snapshot = None
    if data.person_id is not None:
        person = await lock_person_for_snapshot(db, data.person_id)
        if person is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")
        previous_snapshot = await serialize_person_snapshot(db, person)
        if data.is_primary:
            await db.execute(
                update(Image)
                .where(
                    Image.person_id == data.person_id,
                    Image.deleted_at.is_(None),
                    Image.is_primary.is_(True),
                )
                .values(is_primary=False)
            )
    img = Image(**data.model_dump())
    db.add(img)
    if person is not None and previous_snapshot is not None:
        await db.flush()
        previous_snapshot, current_snapshot = await append_relation_version(
            db,
            person,
            previous_snapshot=previous_snapshot,
            changed_by_id=current_user.id,
            change_summary="Dodanie obrazu",
        )
        add_audit_log(
            db,
            context=audit_context_from_request(request, current_user),
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
            extra_metadata={"relation": "images", "operation": "add"},
        )
    await db.flush()
    await db.refresh(img)
    return ImageSchema.model_validate(img)


@router.get(
    "/documents",
    response_model=list[DocumentSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List documents",
)
async def list_documents(
    response: Response,
    person_id: uuid.UUID | None = None,
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "read")),
) -> list[DocumentSchema]:
    query = select(Document).where(Document.deleted_at.is_(None))
    if person_id:
        query = query.where(Document.person_id == person_id)
    query = query.order_by(Document.created_at.desc())
    items, total = await execute_page(db, query, page=page, per_page=per_page)
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [DocumentSchema.model_validate(item) for item in items]


@router.post(
    "/documents",
    response_model=DocumentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create document record",
)
async def create_document(
    data: DocumentCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> DocumentSchema:
    doc = Document(**data.model_dump())
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return DocumentSchema.model_validate(doc)
