"""
Popes REST API router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.pope_service import PopeService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.popes.schemas import PopeCreateSchema, PopeSchema

router = APIRouter()


@router.get("", response_model=list[PopeSchema], summary="List popes")
async def list_popes(
    search: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
) -> list[PopeSchema]:
    popes = await PopeService(db).list_popes(search=search)
    return [PopeSchema.model_validate(pope) for pope in popes]


@router.post(
    "", response_model=PopeSchema, status_code=status.HTTP_201_CREATED, summary="Create pope entry"
)
async def create_pope(
    data: PopeCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "create")),
) -> PopeSchema:
    pope = await PopeService(db).create_pope(data)
    return PopeSchema.model_validate(pope)
