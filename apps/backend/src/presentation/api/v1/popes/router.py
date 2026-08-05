"""
Popes REST API router.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import Pope
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.orders.schemas import PopeCreateSchema, PopeSchema, PopeUpdateSchema

router = APIRouter()


@router.get("", response_model=list[PopeSchema], summary="List popes")
async def list_popes(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[PopeSchema]:
    query = select(Pope).where(Pope.deleted_at.is_(None))
    if search:
        query = query.where(Pope.papal_name.ilike(f"%{search}%") | Pope.birth_name.ilike(f"%{search}%"))
    query = query.order_by(Pope.regnal_number.desc().nullslast(), Pope.created_at.desc())
    res = await db.execute(query)
    return [PopeSchema.model_validate(p) for p in res.scalars().all()]


@router.post("", response_model=PopeSchema, status_code=status.HTTP_201_CREATED, summary="Create pope entry")
async def create_pope(
    data: PopeCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "create")),
) -> PopeSchema:
    pope = Pope(**data.model_dump())
    db.add(pope)
    await db.commit()
    await db.refresh(pope)
    return PopeSchema.model_validate(pope)
