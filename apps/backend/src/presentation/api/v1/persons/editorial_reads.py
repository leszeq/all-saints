"""Protected person read models for the editorial panel."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_query_service import PersonQueryService
from src.domain.hagiography.models import Era, Gender, PersonType, PublicationStatus
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import (
    PersonAdminListItemSchema,
    PersonAdminListResponseSchema,
    PersonDetailSchema,
    PersonListItemSchema,
)

router = APIRouter()


@router.get(
    "/admin",
    response_model=PersonAdminListResponseSchema,
    summary="List persons for the editorial panel",
    description="Protected person list enriched with the latest editor identity.",
)
async def list_persons_for_admin(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(None, max_length=200),
    person_type: PersonType | None = None,
    status_filter: PublicationStatus | None = Query(None, alias="status"),
    gender: Gender | None = None,
    era: Era | None = None,
    country_id: uuid.UUID | None = None,
    is_featured: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> PersonAdminListResponseSchema:
    """Return persons with internal editorial audit data."""
    service = PersonQueryService(db)
    items, total = await service.list_persons(
        page=page,
        per_page=per_page,
        search=search,
        person_type=person_type,
        status=status_filter,
        gender=gender,
        era=era,
        country_id=country_id,
        is_featured=is_featured,
    )
    editors = await service.get_last_editors([person.id for person in items])
    pages = -(-total // per_page) if total > 0 else 1

    admin_items = []
    for person in items:
        admin_items.append(
            PersonAdminListItemSchema(
                **PersonListItemSchema.model_validate(person).model_dump(),
                last_modified_at=person.updated_at,
                last_modified_by=editors.get(person.id),
            )
        )

    return PersonAdminListResponseSchema(
        items=admin_items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/admin/{id_or_slug}",
    response_model=PersonDetailSchema,
    summary="Get person detail for the editorial panel",
    description="Protected detail view that also exposes draft and review records.",
)
async def get_person_for_admin(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> PersonDetailSchema:
    """Fetch any active person for editorial work."""
    person = await PersonQueryService(db).get_by_id_or_slug(id_or_slug)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )
    return PersonDetailSchema.model_validate(person)
