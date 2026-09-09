"""Protected person version-history endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import PersonService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import PersonVersionSchema

router = APIRouter()


@router.get(
    "/{person_id}/versions",
    response_model=list[PersonVersionSchema],
    summary="Get person version history",
)
async def get_person_versions(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> list[PersonVersionSchema]:
    """Get version history snapshots for a person."""
    versions = await PersonService(db).get_person_versions(person_id)
    return [PersonVersionSchema.model_validate(version) for version in versions]
