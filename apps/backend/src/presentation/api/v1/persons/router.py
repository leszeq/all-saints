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

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import (
    PersonService,
    PersonStatusChangeError,
    PersonVersionConflictError,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.catalogue import get_person, list_persons
from src.presentation.api.v1.persons.catalogue import router as catalogue_router
from src.presentation.api.v1.persons.editorial_reads import (
    get_person_for_admin,
    list_persons_for_admin,
)
from src.presentation.api.v1.persons.editorial_reads import router as editorial_reads_router
from src.presentation.api.v1.persons.profile_portability import (
    export_person_profile,
    import_person_profile,
    validate_person_profile_import,
)
from src.presentation.api.v1.persons.profile_portability import (
    router as profile_portability_router,
)
from src.presentation.api.v1.persons.schemas import (
    PersonCreateSchema,
    PersonDetailSchema,
    PersonListResponseSchema,
    PersonUpdateSchema,
    PersonVersionSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()

__all__ = [
    "export_person_profile",
    "get_person",
    "get_person_for_admin",
    "import_person_profile",
    "list_persons",
    "list_persons_for_admin",
    "validate_person_profile_import",
]

# FastAPI cannot include an empty child path into an empty-prefix router, so the
# collection endpoint is registered here while its implementation stays in catalogue.
router.add_api_route(
    "",
    list_persons,
    methods=["GET"],
    response_model=PersonListResponseSchema,
    summary="List persons",
    description="Browse saints, blessed, and candidates with full-text search, multi-criteria filtering, and pagination.",
)
router.include_router(editorial_reads_router)
router.include_router(profile_portability_router)


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
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "create")),
) -> PersonDetailSchema:
    """Create a new person record."""
    service = PersonService(db)
    try:
        person = await service.create_person(
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

    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
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
    """Soft-delete person."""
    service = PersonService(db)
    person = await service.get_by_id_or_slug(str(person_id))

    if not person:
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
    """Restore soft-deleted person."""
    service = PersonService(db)
    person = await service.restore_person(
        person_id,
        user_id=current_user.id,
        audit_context=audit_context_from_request(request, current_user),
    )

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


# Keep the public catch-all slug route after all static editorial routes.
router.include_router(catalogue_router)
