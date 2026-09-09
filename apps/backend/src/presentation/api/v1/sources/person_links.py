"""HTTP adapter for versioned person-to-source assignments."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_source_service import (
    PersonSourceConflictError,
    PersonSourceNotFoundError,
    PersonSourceService,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.schemas import (
    PersonSourceCreateSchema,
    PersonSourceSchema,
    PersonWebSourceCreateSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.get(
    "/person-links/{person_id}",
    response_model=list[PersonSourceSchema],
    summary="List sources assigned to a person",
)
async def list_person_sources(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "read")),
) -> list[PersonSourceSchema]:
    """Return active bibliography and historical-source assignments."""
    links = await PersonSourceService(db).list_sources(person_id)
    return [PersonSourceSchema.model_validate(link) for link in links]


@router.post(
    "/person-links/{person_id}",
    response_model=PersonSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a source to a person",
)
async def create_person_source(
    person_id: uuid.UUID,
    data: PersonSourceCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("sources", "create")),
) -> PersonSourceSchema:
    """Assign an existing source and record the relation in person history."""
    try:
        link = await PersonSourceService(db).create_source(
            person_id,
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except PersonSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PersonSourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PersonSourceSchema.model_validate(link)


@router.post(
    "/person-links/{person_id}/web",
    response_model=PersonSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create and assign a website source to a person",
)
async def create_person_web_source(
    person_id: uuid.UUID,
    data: PersonWebSourceCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("sources", "create")),
) -> PersonSourceSchema:
    """Create or reuse a URL source and attach it in one transaction."""
    try:
        link = await PersonSourceService(db).create_web_source(
            person_id,
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except PersonSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PersonSourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return PersonSourceSchema.model_validate(link)


@router.delete(
    "/person-links/{person_id}/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Remove a source assignment from a person",
)
async def delete_person_source(
    person_id: uuid.UUID,
    link_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("sources", "delete")),
) -> None:
    """Soft-delete one source assignment without deleting the source itself."""
    try:
        await PersonSourceService(db).delete_source(
            person_id,
            link_id,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except PersonSourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
