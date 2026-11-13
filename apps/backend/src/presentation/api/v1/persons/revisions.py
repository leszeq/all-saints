"""Protected endpoints for isolated person-content revisions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import PersonVersionConflictError
from src.application.services.publication_revision_service import (
    PublicationRevisionConflictError,
    PublicationRevisionNotFoundError,
    PublicationRevisionService,
    PublicationRevisionStateError,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import (
    CreatePersonRevisionCommand,
    PersonRevisionSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.get(
    "/{person_id}/revisions/active",
    response_model=PersonRevisionSchema | None,
    summary="Get the active person revision",
    description=(
        "Return the newest draft or review revision so an editor can resume the isolated workflow."
    ),
)
async def get_active_person_revision(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> PersonRevisionSchema | None:
    """Load the active isolated revision without touching the live profile."""
    del current_user
    revision = await PublicationRevisionService(db).get_active_revision(person_id)
    return PersonRevisionSchema.model_validate(revision) if revision is not None else None


@router.post(
    "/{person_id}/revisions",
    response_model=PersonRevisionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Start an isolated person revision",
    description=(
        "Create a draft snapshot from the current published profile without changing live data."
    ),
)
async def create_person_revision(
    person_id: uuid.UUID,
    data: CreatePersonRevisionCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> PersonRevisionSchema:
    """Create one draft revision tied to the editor's expected live version."""
    try:
        revision = await PublicationRevisionService(db).create_draft(
            person_id,
            expected_version=data.expected_version,
            author_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            change_summary=data.change_summary,
        )
    except PublicationRevisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PublicationRevisionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PublicationRevisionConflictError as exc:
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
    return PersonRevisionSchema.model_validate(revision)
