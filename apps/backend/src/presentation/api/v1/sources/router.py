"""
Sources & Media API router (Bibliography, Historical Sources, Images, Documents).
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.identity.models import User
from src.domain.sources.models import Bibliography, Document, HistoricalSource, Image
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.schemas import (
    BibliographyCreateSchema,
    BibliographySchema,
    DocumentCreateSchema,
    DocumentSchema,
    HistoricalSourceCreateSchema,
    HistoricalSourceSchema,
    ImageCreateSchema,
    ImageSchema,
)

router = APIRouter()


# ==============================================================================
# BIBLIOGRAPHY
# ==============================================================================


@router.get("/bibliography", response_model=list[BibliographySchema], summary="List bibliography entries")
async def list_bibliography(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[BibliographySchema]:
    query = select(Bibliography).where(Bibliography.deleted_at.is_(None))
    if search:
        query = query.where(Bibliography.title.ilike(f"%{search}%") | Bibliography.authors.ilike(f"%{search}%"))
    query = query.order_by(Bibliography.year.desc().nullslast(), Bibliography.title.asc()).limit(100)
    res = await db.execute(query)
    return [BibliographySchema.model_validate(b) for b in res.scalars().all()]


@router.post("/bibliography", response_model=BibliographySchema, status_code=status.HTTP_201_CREATED, summary="Create bibliography entry")
async def create_bibliography(
    data: BibliographyCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> BibliographySchema:
    bib = Bibliography(**data.model_dump())
    db.add(bib)
    await db.commit()
    await db.refresh(bib)
    return BibliographySchema.model_validate(bib)


# ==============================================================================
# HISTORICAL SOURCES
# ==============================================================================


@router.get("/historical-sources", response_model=list[HistoricalSourceSchema], summary="List primary historical sources")
async def list_historical_sources(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[HistoricalSourceSchema]:
    query = select(HistoricalSource).where(HistoricalSource.deleted_at.is_(None))
    if search:
        query = query.where(HistoricalSource.title.ilike(f"%{search}%") | HistoricalSource.repository.ilike(f"%{search}%"))
    query = query.order_by(HistoricalSource.title.asc()).limit(100)
    res = await db.execute(query)
    return [HistoricalSourceSchema.model_validate(s) for s in res.scalars().all()]


@router.post("/historical-sources", response_model=HistoricalSourceSchema, status_code=status.HTTP_201_CREATED, summary="Create historical source")
async def create_historical_source(
    data: HistoricalSourceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> HistoricalSourceSchema:
    src = HistoricalSource(**data.model_dump())
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return HistoricalSourceSchema.model_validate(src)


# ==============================================================================
# IMAGES
# ==============================================================================


@router.get("/images", response_model=list[ImageSchema], summary="List images")
async def list_images(
    person_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[ImageSchema]:
    query = select(Image).where(Image.deleted_at.is_(None))
    if person_id:
        query = query.where(Image.person_id == person_id)
    query = query.order_by(Image.is_primary.desc(), Image.sort_order.asc()).limit(100)
    res = await db.execute(query)
    return [ImageSchema.model_validate(i) for i in res.scalars().all()]


@router.post("/images", response_model=ImageSchema, status_code=status.HTTP_201_CREATED, summary="Create image record")
async def create_image(
    data: ImageCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("images", "create")),
) -> ImageSchema:
    img = Image(**data.model_dump())
    db.add(img)
    await db.commit()
    await db.refresh(img)
    return ImageSchema.model_validate(img)


# ==============================================================================
# DOCUMENTS
# ==============================================================================


@router.get("/documents", response_model=list[DocumentSchema], summary="List documents")
async def list_documents(
    person_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[DocumentSchema]:
    query = select(Document).where(Document.deleted_at.is_(None))
    if person_id:
        query = query.where(Document.person_id == person_id)
    query = query.order_by(Document.created_at.desc()).limit(100)
    res = await db.execute(query)
    return [DocumentSchema.model_validate(d) for d in res.scalars().all()]


@router.post("/documents", response_model=DocumentSchema, status_code=status.HTTP_201_CREATED, summary="Create document record")
async def create_document(
    data: DocumentCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> DocumentSchema:
    doc = Document(**data.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return DocumentSchema.model_validate(doc)
