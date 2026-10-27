"""Public read endpoints for taxonomy dictionaries."""

from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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
    PatronageConceptPersonsSchema,
    PatronageConceptSchema,
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


@router.get(
    "/patronages",
    response_model=list[PatronageConceptSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List public patronage concepts",
)
async def list_patronages(
    response: Response,
    search: str | None = Query(None, min_length=2, max_length=100),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[PatronageConceptSchema]:
    concepts, total = await TaxonomyService(db).list_patronage_concepts(
        search=search,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [PatronageConceptSchema.model_validate(asdict(concept)) for concept in concepts]


@router.get(
    "/patronages/{slug}/persons",
    response_model=PatronageConceptPersonsSchema,
    summary="List people assigned to a patronage concept",
)
async def list_patronage_persons(
    slug: str,
    page: PageNumber = 1,
    per_page: PageSize = 20,
    db: AsyncSession = Depends(get_db_session),
) -> PatronageConceptPersonsSchema:
    service = TaxonomyService(db)
    concept = await service.get_patronage_concept(slug)
    if concept is None:
        raise HTTPException(status_code=404, detail="Patronat nie został znaleziony")
    persons, total = await service.list_persons_for_patronage(
        concept,
        page=page,
        per_page=per_page,
    )
    pages = -(-total // per_page) if total > 0 else 1
    return PatronageConceptPersonsSchema(
        concept=PatronageConceptSchema.model_validate(asdict(concept)),
        items=persons,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
