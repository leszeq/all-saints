"""
Religious Orders REST API router.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.geography.models import ReligiousOrder
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.orders.schemas import (
    ReligiousOrderCreateSchema,
    ReligiousOrderSchema,
    ReligiousOrderUpdateSchema,
)

router = APIRouter()


@router.get("", response_model=list[ReligiousOrderSchema], summary="List religious orders")
async def list_orders(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[ReligiousOrderSchema]:
    query = select(ReligiousOrder).where(ReligiousOrder.deleted_at.is_(None))
    if search:
        query = query.where(
            ReligiousOrder.name.ilike(f"%{search}%") | ReligiousOrder.abbreviation.ilike(f"%{search}%")
        )
    query = query.order_by(ReligiousOrder.name.asc())
    res = await db.execute(query)
    return [ReligiousOrderSchema.model_validate(o) for o in res.scalars().all()]


@router.post("", response_model=ReligiousOrderSchema, status_code=status.HTTP_201_CREATED, summary="Create religious order")
async def create_order(
    data: ReligiousOrderCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("orders", "create")),
) -> ReligiousOrderSchema:
    order = ReligiousOrder(**data.model_dump())
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return ReligiousOrderSchema.model_validate(order)
