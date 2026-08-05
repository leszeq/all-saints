"""
Taxonomy API router (Categories, Tags, States of Life, Occupations).
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import Category, Occupation, StateOfLife, Tag
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.taxonomy.schemas import (
    CategoryCreateSchema,
    CategorySchema,
    OccupationSchema,
    StateOfLifeSchema,
    TagCreateSchema,
    TagSchema,
)

router = APIRouter()


# ==============================================================================
# CATEGORIES
# ==============================================================================


@router.get("/categories", response_model=list[CategorySchema], summary="List categories")
async def list_categories(
    parent_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[CategorySchema]:
    query = select(Category).where(Category.deleted_at.is_(None))
    if parent_id is not None:
        query = query.where(Category.parent_id == parent_id)
    query = query.order_by(Category.sort_order.asc(), Category.name_pl.asc())
    res = await db.execute(query)
    return [CategorySchema.model_validate(c) for c in res.scalars().all()]


@router.post("/categories", response_model=CategorySchema, status_code=status.HTTP_201_CREATED, summary="Create category")
async def create_category(
    data: CategoryCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "create")),
) -> CategorySchema:
    slug = slugify(data.name_pl)
    cat = Category(slug=slug, **data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategorySchema.model_validate(cat)


# ==============================================================================
# TAGS
# ==============================================================================


@router.get("/tags", response_model=list[TagSchema], summary="List tags")
async def list_tags(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[TagSchema]:
    query = select(Tag).where(Tag.deleted_at.is_(None))
    if search:
        query = query.where(Tag.name_pl.ilike(f"%{search}%") | Tag.name_en.ilike(f"%{search}%"))
    query = query.order_by(Tag.name_pl.asc())
    res = await db.execute(query)
    return [TagSchema.model_validate(t) for t in res.scalars().all()]


@router.post("/tags", response_model=TagSchema, status_code=status.HTTP_201_CREATED, summary="Create tag")
async def create_tag(
    data: TagCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "create")),
) -> TagSchema:
    slug = slugify(data.name_pl)
    tag = Tag(slug=slug, **data.model_dump())
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagSchema.model_validate(tag)


# ==============================================================================
# STATES OF LIFE
# ==============================================================================


@router.get("/states-of-life", response_model=list[StateOfLifeSchema], summary="List states of life")
async def list_states_of_life(
    db: AsyncSession = Depends(get_db_session),
) -> list[StateOfLifeSchema]:
    query = select(StateOfLife).order_by(StateOfLife.name_pl.asc())
    res = await db.execute(query)
    return [StateOfLifeSchema.model_validate(s) for s in res.scalars().all()]


# ==============================================================================
# OCCUPATIONS
# ==============================================================================


@router.get("/occupations", response_model=list[OccupationSchema], summary="List occupations")
async def list_occupations(
    db: AsyncSession = Depends(get_db_session),
) -> list[OccupationSchema]:
    query = select(Occupation).order_by(Occupation.name_pl.asc())
    res = await db.execute(query)
    return [OccupationSchema.model_validate(o) for o in res.scalars().all()]
