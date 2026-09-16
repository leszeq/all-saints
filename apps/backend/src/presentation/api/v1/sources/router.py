"""Sources API router for statistics and source catalogues."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.source_catalogue_service import (
    SourceCatalogueNotFoundError,
    SourceCatalogueService,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.media import router as media_router
from src.presentation.api.v1.sources.person_links import router as person_links_router
from src.presentation.api.v1.sources.schemas import (
    BibliographyCreateSchema,
    BibliographySchema,
    BibliographyUpdateSchema,
    HistoricalSourceCreateSchema,
    HistoricalSourceSchema,
    HistoricalSourceUpdateSchema,
    SourceStatsSchema,
)

router = APIRouter()


# ==============================================================================
# BIBLIOGRAPHY
# ==============================================================================


@router.get("/stats", response_model=SourceStatsSchema, summary="Get public source statistics")
async def get_source_stats(
    db: AsyncSession = Depends(get_db_session),
) -> SourceStatsSchema:
    stats = await SourceCatalogueService(db).get_public_stats()
    return SourceStatsSchema.model_validate(stats)


@router.get(
    "/bibliography",
    response_model=list[BibliographySchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List bibliography entries",
)
async def list_bibliography(
    response: Response,
    search: str | None = Query(None, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[BibliographySchema]:
    items, total = await SourceCatalogueService(db).list_bibliography(
        search=search,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [BibliographySchema.model_validate(item) for item in items]


@router.post(
    "/bibliography",
    response_model=BibliographySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create bibliography entry",
)
async def create_bibliography(
    data: BibliographyCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> BibliographySchema:
    bibliography = await SourceCatalogueService(db).create_bibliography(data)
    return BibliographySchema.model_validate(bibliography)


@router.patch(
    "/bibliography/{bibliography_id}",
    response_model=BibliographySchema,
    summary="Update bibliography entry",
)
async def update_bibliography(
    bibliography_id: uuid.UUID,
    data: BibliographyUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "update")),
) -> BibliographySchema:
    try:
        bibliography = await SourceCatalogueService(db).update_bibliography(bibliography_id, data)
    except SourceCatalogueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BibliographySchema.model_validate(bibliography)


# ==============================================================================
# HISTORICAL SOURCES
# ==============================================================================


@router.get(
    "/historical-sources",
    response_model=list[HistoricalSourceSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List primary historical sources",
)
async def list_historical_sources(
    response: Response,
    search: str | None = Query(None, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[HistoricalSourceSchema]:
    items, total = await SourceCatalogueService(db).list_historical_sources(
        search=search,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [HistoricalSourceSchema.model_validate(item) for item in items]


@router.post(
    "/historical-sources",
    response_model=HistoricalSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create historical source",
)
async def create_historical_source(
    data: HistoricalSourceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "create")),
) -> HistoricalSourceSchema:
    source = await SourceCatalogueService(db).create_historical_source(data)
    return HistoricalSourceSchema.model_validate(source)


@router.patch(
    "/historical-sources/{source_id}",
    response_model=HistoricalSourceSchema,
    summary="Update historical source",
)
async def update_historical_source(
    source_id: uuid.UUID,
    data: HistoricalSourceUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "update")),
) -> HistoricalSourceSchema:
    try:
        source = await SourceCatalogueService(db).update_historical_source(source_id, data)
    except SourceCatalogueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return HistoricalSourceSchema.model_validate(source)


router.include_router(person_links_router)
router.include_router(media_router)
