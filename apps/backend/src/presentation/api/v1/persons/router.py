"""
Persons REST API router.

Endpoints:
- GET    /persons                     – List persons (search, filter, paginate)
- POST   /persons                     – Create a new person
- GET    /persons/{id_or_slug}        – Get details of a person
- PATCH  /persons/{id}                – Update a person (with versioning)
- DELETE /persons/{id}                – Soft-delete a person
- POST   /persons/{id}/restore        – Restore soft-deleted person
- GET    /persons/{id}/versions       – Get version history
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import PersonService
from src.domain.hagiography.models import Era, Gender, PersonType, PublicationStatus
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import get_current_user, require_permission
from src.presentation.api.v1.persons.schemas import (
    PersonCreateSchema,
    PersonDetailSchema,
    PersonListItemSchema,
    PersonListResponseSchema,
    PersonUpdateSchema,
    PersonVersionSchema,
)

router = APIRouter()


@router.get(
    "",
    response_model=PersonListResponseSchema,
    summary="List persons",
    description="Browse saints, blessed, and candidates with full-text search, multi-criteria filtering, and pagination.",
)
async def list_persons(
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
) -> PersonListResponseSchema:
    """List persons with optional filters."""
    service = PersonService(db)
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

    pages = -(-total // per_page) if total > 0 else 1

    return PersonListResponseSchema(
        items=[PersonListItemSchema.model_validate(p) for p in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post(
    "",
    response_model=PersonDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create person",
    description="Create a new person entry in the hagiographic catalogue.",
    responses={
        201: {"description": "Person created together with the first version snapshot"},
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Missing persons:create permission"},
        409: {"description": "Database constraint conflict"},
        422: {"description": "Payload validation failed"},
    },
)
async def create_person(
    data: PersonCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "create")),
) -> PersonDetailSchema:
    """Create a new person record."""
    service = PersonService(db)
    person = await service.create_person(data, user_id=current_user.id)
    return PersonDetailSchema.model_validate(person)


@router.get(
    "/{id_or_slug}",
    response_model=PersonDetailSchema,
    summary="Get person detail",
    description="Fetch a single person by UUID or URL slug.",
)
async def get_person(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> PersonDetailSchema:
    """Fetch person details."""
    service = PersonService(db)
    person = await service.get_by_id_or_slug(id_or_slug)

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )

    return PersonDetailSchema.model_validate(person)


@router.patch(
    "/{person_id}",
    response_model=PersonDetailSchema,
    summary="Update person",
    description="Update fields of a person record. Creates a new version snapshot automatically.",
)
async def update_person(
    person_id: uuid.UUID,
    data: PersonUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> PersonDetailSchema:
    """Update an existing person record."""
    service = PersonService(db)
    person = await service.get_by_id_or_slug(str(person_id))

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )

    updated_person = await service.update_person(person, data, user_id=current_user.id)
    return PersonDetailSchema.model_validate(updated_person)


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Soft-delete person",
    description="Soft-delete a person entry.",
)
async def delete_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "delete")),
) -> None:
    """Soft-delete person."""
    service = PersonService(db)
    person = await service.get_by_id_or_slug(str(person_id))

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )

    await service.soft_delete_person(person, user_id=current_user.id)


@router.post(
    "/{person_id}/restore",
    response_model=PersonDetailSchema,
    summary="Restore soft-deleted person",
)
async def restore_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "restore")),
) -> PersonDetailSchema:
    """Restore soft-deleted person."""
    service = PersonService(db)
    person = await service.restore_person(person_id)

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona lub nie była usunięta",
        )

    return PersonDetailSchema.model_validate(person)


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
    service = PersonService(db)
    versions = await service.get_person_versions(person_id)
    return [PersonVersionSchema.model_validate(v) for v in versions]
