"""
Geography API router (Countries, Dioceses, Places, Churches).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.geography.models import Church, Country, Diocese, Place
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import get_current_user, require_permission
from src.presentation.api.v1.geography.schemas import (
    ChurchCreateSchema,
    ChurchSchema,
    ChurchUpdateSchema,
    CountryCreateSchema,
    CountrySchema,
    CountryUpdateSchema,
    DioceseCreateSchema,
    DioceseSchema,
    DioceseUpdateSchema,
    PlaceCreateSchema,
    PlaceSchema,
    PlaceUpdateSchema,
)

router = APIRouter()


# ==============================================================================
# COUNTRIES
# ==============================================================================


@router.get("/countries", response_model=list[CountrySchema], summary="List countries")
async def list_countries(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[CountrySchema]:
    query = select(Country).where(Country.deleted_at.is_(None))
    if search:
        query = query.where(Country.name_pl.ilike(f"%{search}%") | Country.name_en.ilike(f"%{search}%"))
    query = query.order_by(Country.name_pl.asc())
    res = await db.execute(query)
    return [CountrySchema.model_validate(c) for c in res.scalars().all()]


@router.post("/countries", response_model=CountrySchema, status_code=status.HTTP_201_CREATED, summary="Create country")
async def create_country(
    data: CountryCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> CountrySchema:
    country = Country(**data.model_dump())
    db.add(country)
    await db.commit()
    await db.refresh(country)
    return CountrySchema.model_validate(country)


# ==============================================================================
# DIOCESES
# ==============================================================================


@router.get("/dioceses", response_model=list[DioceseSchema], summary="List dioceses")
async def list_dioceses(
    country_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[DioceseSchema]:
    query = select(Diocese).where(Diocese.deleted_at.is_(None))
    if country_id:
        query = query.where(Diocese.country_id == country_id)
    query = query.order_by(Diocese.name.asc())
    res = await db.execute(query)
    return [DioceseSchema.model_validate(d) for d in res.scalars().all()]


@router.post("/dioceses", response_model=DioceseSchema, status_code=status.HTTP_201_CREATED, summary="Create diocese")
async def create_diocese(
    data: DioceseCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> DioceseSchema:
    diocese = Diocese(**data.model_dump())
    db.add(diocese)
    await db.commit()
    await db.refresh(diocese)
    return DioceseSchema.model_validate(diocese)


# ==============================================================================
# PLACES
# ==============================================================================


@router.get("/places", response_model=list[PlaceSchema], summary="List places")
async def list_places(
    country_id: uuid.UUID | None = None,
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[PlaceSchema]:
    query = select(Place).where(Place.deleted_at.is_(None))
    if country_id:
        query = query.where(Place.country_id == country_id)
    if search:
        query = query.where(Place.name.ilike(f"%{search}%"))
    query = query.order_by(Place.name.asc()).limit(100)
    res = await db.execute(query)
    return [PlaceSchema.model_validate(p) for p in res.scalars().all()]


@router.post("/places", response_model=PlaceSchema, status_code=status.HTTP_201_CREATED, summary="Create place")
async def create_place(
    data: PlaceCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> PlaceSchema:
    place = Place(**data.model_dump())
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return PlaceSchema.model_validate(place)


# ==============================================================================
# CHURCHES
# ==============================================================================


@router.get("/churches", response_model=list[ChurchSchema], summary="List churches")
async def list_churches(
    place_id: uuid.UUID | None = None,
    is_sanctuary: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[ChurchSchema]:
    query = select(Church).where(Church.deleted_at.is_(None))
    if place_id:
        query = query.where(Church.place_id == place_id)
    if is_sanctuary is not None:
        query = query.where(Church.is_national_sanctuary == is_sanctuary)
    query = query.order_by(Church.name.asc()).limit(100)
    res = await db.execute(query)
    return [ChurchSchema.model_validate(c) for c in res.scalars().all()]


@router.post("/churches", response_model=ChurchSchema, status_code=status.HTTP_201_CREATED, summary="Create church")
async def create_church(
    data: ChurchCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("geography", "create")),
) -> ChurchSchema:
    church = Church(**data.model_dump())
    db.add(church)
    await db.commit()
    await db.refresh(church)
    return ChurchSchema.model_validate(church)
