"""Lightweight public URL indexes used by crawlers and sitemap generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_query_service import (
    PersonQueryService,
    PublicIndexCursorError,
)
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.persons.schemas import (
    PublicIndexItemSchema,
    PublicIndexResponseSchema,
)

router = APIRouter()


@router.get(
    "/persons",
    response_model=PublicIndexResponseSchema,
    summary="List public person URLs",
)
async def list_public_person_urls(
    cursor: str | None = Query(None, max_length=512),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
) -> PublicIndexResponseSchema:
    """Return only published profile identifiers and their update timestamps."""
    try:
        page = await PersonQueryService(db).list_public_index(cursor=cursor, limit=limit)
    except PublicIndexCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return PublicIndexResponseSchema(
        items=[PublicIndexItemSchema.model_validate(item) for item in page.items],
        next_cursor=page.next_cursor,
    )
