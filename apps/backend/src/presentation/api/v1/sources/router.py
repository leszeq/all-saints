"""Sources API router for statistics and source catalogues."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.identity.models import User
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
)
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
    execute_page,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.media import router as media_router
from src.presentation.api.v1.sources.person_links import router as person_links_router
from src.presentation.api.v1.sources.schemas import (
    BibliographyCreateSchema,
    BibliographySchema,
    HistoricalSourceCreateSchema,
    HistoricalSourceSchema,
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
    published_person_filter = (
        Person.deleted_at.is_(None),
        Person.status == PublicationStatus.PUBLISHED.value,
    )
    active_person_source_filter = (
        PersonSource.deleted_at.is_(None),
        or_(
            and_(
                PersonSource.bibliography_id.is_not(None),
                PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
            ),
            and_(
                PersonSource.historical_source_id.is_not(None),
                PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
            ),
        ),
    )

    total_published_persons = (
        await db.execute(select(func.count(Person.id)).where(*published_person_filter))
    ).scalar_one()
    documented_persons = (
        await db.execute(
            select(func.count(func.distinct(PersonSource.person_id)))
            .join(Person, Person.id == PersonSource.person_id)
            .where(*published_person_filter, *active_person_source_filter)
        )
    ).scalar_one()
    person_source_links = (
        await db.execute(
            select(func.count(PersonSource.id))
            .join(Person, Person.id == PersonSource.person_id)
            .where(*published_person_filter, *active_person_source_filter)
        )
    ).scalar_one()
    bibliography_sources = (
        await db.execute(
            select(func.count(Bibliography.id)).where(Bibliography.deleted_at.is_(None))
        )
    ).scalar_one()
    historical_sources = (
        await db.execute(
            select(func.count(HistoricalSource.id)).where(HistoricalSource.deleted_at.is_(None))
        )
    ).scalar_one()
    images = (
        await db.execute(
            select(func.count(Image.id))
            .join(Person, Person.id == Image.person_id)
            .where(*published_person_filter, Image.deleted_at.is_(None))
        )
    ).scalar_one()
    unknown_license_images = (
        await db.execute(
            select(func.count(Image.id))
            .join(Person, Person.id == Image.person_id)
            .where(
                *published_person_filter,
                Image.deleted_at.is_(None),
                Image.license == ImageLicense.UNKNOWN.value,
            )
        )
    ).scalar_one()

    return SourceStatsSchema(
        bibliography_sources=bibliography_sources,
        historical_sources=historical_sources,
        person_source_links=person_source_links,
        documented_persons=documented_persons,
        total_published_persons=total_published_persons,
        images=images,
        unknown_license_images=unknown_license_images,
    )


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
    query = select(Bibliography).where(Bibliography.deleted_at.is_(None))
    if search:
        query = query.where(
            Bibliography.title.ilike(f"%{search}%") | Bibliography.authors.ilike(f"%{search}%")
        )
    query = query.order_by(Bibliography.year.desc().nullslast(), Bibliography.title.asc())
    items, total = await execute_page(db, query, page=page, per_page=per_page)
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
    bib = Bibliography(**data.model_dump())
    db.add(bib)
    await db.flush()
    await db.refresh(bib)
    return BibliographySchema.model_validate(bib)


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
    query = select(HistoricalSource).where(HistoricalSource.deleted_at.is_(None))
    if search:
        query = query.where(
            HistoricalSource.title.ilike(f"%{search}%")
            | HistoricalSource.repository.ilike(f"%{search}%")
        )
    query = query.order_by(HistoricalSource.title.asc())
    items, total = await execute_page(db, query, page=page, per_page=per_page)
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
    src = HistoricalSource(**data.model_dump())
    db.add(src)
    await db.flush()
    await db.refresh(src)
    return HistoricalSourceSchema.model_validate(src)


router.include_router(person_links_router)
router.include_router(media_router)
