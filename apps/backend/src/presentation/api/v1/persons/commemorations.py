"""Public commemorations attached to published person profiles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.calendar_query_service import CalendarQueryService
from src.application.services.person_query_service import PersonQueryService
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.calendar.schemas import PublicPersonCommemorationSchema

router = APIRouter()


@router.get(
    "/{id_or_slug}/commemorations",
    response_model=list[PublicPersonCommemorationSchema],
    summary="List public person commemorations",
    description=(
        "Return active fixed-date commemorations from active calendars for a published person. "
        "Moveable and editorial-only entries are excluded."
    ),
)
async def list_public_person_commemorations(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> list[PublicPersonCommemorationSchema]:
    """Resolve a published person and expose only the safe calendar projection."""
    person = await PersonQueryService(db).get_by_id_or_slug(
        id_or_slug,
        published_only=True,
        include_translations=False,
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )
    entries = await CalendarQueryService(db).list_public_person_entries(person.id)
    return [PublicPersonCommemorationSchema.model_validate(entry) for entry in entries]
