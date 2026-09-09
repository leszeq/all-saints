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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.media_service import (
    MediaPersonNotFoundError,
    MediaService,
)
from src.domain.identity.models import User
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
    try:
        image = await MediaService(db).create_image(
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except MediaPersonNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ImageSchema.model_validate(image)


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
    document = await MediaService(db).create_document(data)
    return DocumentSchema.model_validate(document)
