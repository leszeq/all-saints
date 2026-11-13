"""Protected mutation endpoints for isolated person revisions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_service import PersonVersionConflictError
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
    PersonRevisionReviewDecisionCommand,
    PersonRevisionSchema,
    PersonRevisionWorkflowCommand,
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


@router.post(
    "/{revision_id}/submit",
    response_model=PersonRevisionSchema,
    summary="Submit a person revision for review",
)
async def submit_person_revision(
    revision_id: uuid.UUID,
    data: PersonRevisionWorkflowCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "submit")),
) -> PersonRevisionSchema:
    """Move a draft revision to review without changing public content."""
    try:
        revision = await PublicationRevisionService(db).submit_for_review(
            revision_id,
            expected_version=data.expected_version,
            author_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            note=data.note,
        )
    except PublicationRevisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PublicationRevisionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
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


@router.post(
    "/{revision_id}/return",
    response_model=PersonRevisionSchema,
    summary="Return a person revision to the editor",
)
async def return_person_revision(
    revision_id: uuid.UUID,
    data: PersonRevisionReviewDecisionCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "review")),
) -> PersonRevisionSchema:
    """Return a review revision to draft with an explanation for the editor."""
    try:
        revision = await PublicationRevisionService(db).return_to_draft(
            revision_id,
            expected_version=data.expected_version,
            note=data.note,
            author_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
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


@router.post(
    "/{revision_id}/reject",
    response_model=PersonRevisionSchema,
    summary="Reject a person revision",
)
async def reject_person_revision(
    revision_id: uuid.UUID,
    data: PersonRevisionReviewDecisionCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "review")),
) -> PersonRevisionSchema:
    """Reject a review revision while retaining its audit history."""
    try:
        revision = await PublicationRevisionService(db).reject(
            revision_id,
            expected_version=data.expected_version,
            note=data.note,
            author_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
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


@router.post(
    "/{revision_id}/publish",
    response_model=PersonRevisionSchema,
    summary="Publish a reviewed person revision",
    description=(
        "Apply the reviewed scalar profile snapshot to the live person atomically and mark it published."
    ),
)
async def publish_person_revision(
    revision_id: uuid.UUID,
    data: PersonRevisionWorkflowCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "review")),
) -> PersonRevisionSchema:
    """Publish a review revision using the reviewer permission."""
    try:
        revision = await PublicationRevisionService(db).publish(
            revision_id,
            expected_version=data.expected_version,
            author_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            note=data.note,
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
