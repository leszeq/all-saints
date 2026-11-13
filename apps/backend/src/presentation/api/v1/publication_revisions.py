"""Protected mutation endpoints for isolated person revisions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.publication_revision_service import (
    PublicationRevisionNotFoundError,
    PublicationRevisionPayloadError,
    PublicationRevisionService,
    PublicationRevisionStateError,
    PublicationRevisionVersionConflictError,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import (
    PersonRevisionSchema,
    UpdatePersonRevisionCommand,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.patch(
    "/{revision_id}",
    response_model=PersonRevisionSchema,
    summary="Update an isolated person revision",
    description=(
        "Merge editable profile fields into a draft revision without changing the public profile."
    ),
)
async def update_person_revision(
    revision_id: uuid.UUID,
    data: UpdatePersonRevisionCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> PersonRevisionSchema:
    """Patch one draft revision using its optimistic-lock version."""
    try:
        revision = await PublicationRevisionService(db).update_draft(
            revision_id,
            expected_version=data.expected_version,
            changes=data.changes,
            author_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            change_summary=data.change_summary,
        )
    except PublicationRevisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PublicationRevisionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PublicationRevisionPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "details": exc.details},
        ) from exc
    except PublicationRevisionVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "code": "publication_revision_version_conflict",
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        ) from exc
    return PersonRevisionSchema.model_validate(revision)
