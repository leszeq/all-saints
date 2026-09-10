"""Public read endpoints for geography reference data."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.geography_service import GeographyService
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
)
from src.presentation.api.v1.geography.schemas import (
    ChurchSchema,
    CountrySchema,
    DioceseSchema,
    PlaceSchema,
)

router = APIRouter()


@router.get("/countries", response_model=list[CountrySchema], summary="List countries")
async def list_countries(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[CountrySchema]:
    countries = await GeographyService(db).list_countries(search=search)
    return [CountrySchema.model_validate(country) for country in countries]


@router.get(
    "/dioceses",
    response_model=list[DioceseSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List dioceses",
)
async def list_dioceses(
    response: Response,
    country_id: uuid.UUID | None = None,
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[DioceseSchema]:
    items, total = await GeographyService(db).list_dioceses(
        country_id=country_id,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [DioceseSchema.model_validate(item) for item in items]


@router.get(
    "/places",
    response_model=list[PlaceSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List places",
)
async def list_places(
    response: Response,
    country_id: uuid.UUID | None = None,
    search: str | None = Query(None, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[PlaceSchema]:
    items, total = await GeographyService(db).list_places(
        country_id=country_id,
        search=search,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [PlaceSchema.model_validate(item) for item in items]


@router.get(
    "/churches",
    response_model=list[ChurchSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List churches",
)
async def list_churches(
    response: Response,
    place_id: uuid.UUID | None = None,
    is_sanctuary: bool | None = None,
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[ChurchSchema]:
    items, total = await GeographyService(db).list_churches(
        place_id=place_id,
        is_sanctuary=is_sanctuary,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [ChurchSchema.model_validate(item) for item in items]
