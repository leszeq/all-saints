"""Public read endpoints for taxonomy dictionaries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.taxonomy_service import TaxonomyService
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
)
from src.presentation.api.v1.taxonomy.schemas import (
    CategorySchema,
    OccupationSchema,
    StateOfLifeSchema,
    TagSchema,
)

router = APIRouter()


@router.get("/categories", response_model=list[CategorySchema], summary="List categories")
async def list_categories(
    parent_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[CategorySchema]:
    categories = await TaxonomyService(db).list_categories(parent_id=parent_id)
    return [CategorySchema.model_validate(category) for category in categories]


@router.get(
    "/tags",
    response_model=list[TagSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List tags",
)
async def list_tags(
    response: Response,
    search: str | None = Query(None, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[TagSchema]:
    items, total = await TaxonomyService(db).list_tags(
        search=search,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [TagSchema.model_validate(item) for item in items]


@router.get(
    "/states-of-life",
    response_model=list[StateOfLifeSchema],
    summary="List states of life",
)
async def list_states_of_life(
    db: AsyncSession = Depends(get_db_session),
) -> list[StateOfLifeSchema]:
    states = await TaxonomyService(db).list_states_of_life()
    return [StateOfLifeSchema.model_validate(state) for state in states]


@router.get(
    "/occupations",
    response_model=list[OccupationSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List occupations",
)
async def list_occupations(
    response: Response,
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[OccupationSchema]:
    items, total = await TaxonomyService(db).list_occupations(
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [OccupationSchema.model_validate(item) for item in items]
