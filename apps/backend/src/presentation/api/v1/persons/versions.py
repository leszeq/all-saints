"""Protected person version-history endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_query_service import PersonQueryService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import (
    PersonVersionListResponseSchema,
    PersonVersionSchema,
)

router = APIRouter()


@router.get(
    "/{person_id}/versions",
    response_model=PersonVersionListResponseSchema,
    summary="Get person version history",
)
async def get_person_versions(
    person_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Numer strony historii wersji"),
    per_page: int = Query(20, ge=1, le=100, description="Liczba wersji na stronie"),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> PersonVersionListResponseSchema:
    """Get one bounded page of version history snapshots for a person."""
    version_page = await PersonQueryService(db).get_person_versions_page(
        person_id,
        page=page,
        per_page=per_page,
    )
    pages = max(1, -(-version_page.total // version_page.per_page))
    return PersonVersionListResponseSchema(
        items=[PersonVersionSchema.model_validate(version) for version in version_page.versions],
        total=version_page.total,
        page=version_page.page,
        per_page=version_page.per_page,
        pages=pages,
    )
