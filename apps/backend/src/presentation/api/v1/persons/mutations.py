"""Protected person create, update, delete, and restore endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import (
    PersonService,
    PersonStatusChangeError,
    PersonVersionConflictError,
)
from src.domain.hagiography.models import PublicationStatus
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import (
    PersonCreateSchema,
    PersonDetailSchema,
    PersonUpdateSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


async def create_person(
    data: PersonCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "create")),
) -> PersonDetailSchema:
    """Create a new person record."""
    try:
        person = await PersonService(db).create_person(
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except PersonStatusChangeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
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
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> PersonDetailSchema:
    """Update an existing person record."""
    service = PersonService(db)
    person = await service.get_by_id_or_slug(str(person_id))
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )
    if person.status == PublicationStatus.PUBLISHED.value and not current_user.has_permission(
        "persons", "publish"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Edycja opublikowanego profilu wymaga uprawnienia persons:publish",
        )

    try:
        updated_person = await service.update_person(
            person,
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except PersonStatusChangeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PersonVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "code": "person_version_conflict",
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        ) from exc
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
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "delete")),
) -> None:
    """Soft-delete a person."""
    service = PersonService(db)
    person = await service.get_by_id_or_slug(str(person_id))
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )

    await service.soft_delete_person(
        person,
        user_id=current_user.id,
        audit_context=audit_context_from_request(request, current_user),
    )


@router.post(
    "/{person_id}/restore",
    response_model=PersonDetailSchema,
    summary="Restore soft-deleted person",
)
async def restore_person(
    person_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "restore")),
) -> PersonDetailSchema:
    """Restore a soft-deleted person."""
    person = await PersonService(db).restore_person(
        person_id,
        user_id=current_user.id,
        audit_context=audit_context_from_request(request, current_user),
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona lub nie była usunięta",
        )
    return PersonDetailSchema.model_validate(person)
