"""Protected human decisions for generated AI suggestions."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.application.services.ai_suggestion_decision_service import (
    AISuggestionDecisionError,
    AISuggestionDecisionService,
    AISuggestionNotFoundError,
)
from src.application.services.person_service import PersonVersionConflictError
from src.application.services.published_content_guard import PublishedContentChangeError
from src.domain.identity.models import User
from src.presentation.api.v1.ai.dependencies import (
    get_ai_suggestion_decision_service,
)
from src.presentation.api.v1.ai.schemas import (
    AISuggestionDecisionRequest,
    AISuggestionDecisionResponse,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.post(
    "/suggestions/{kind}/{person_id}/decision",
    response_model=AISuggestionDecisionResponse,
    summary="Accept or reject an AI editorial suggestion",
    description=(
        "Applies an explicit human decision to a pending summary or tag proposal. "
        "Accepted content is versioned and AI never publishes a profile automatically."
    ),
)
async def decide_ai_suggestion(
    kind: Literal["summary", "tags"],
    person_id: uuid.UUID,
    data: AISuggestionDecisionRequest,
    request: Request,
    service: Annotated[
        AISuggestionDecisionService,
        Depends(get_ai_suggestion_decision_service),
    ],
    current_user: Annotated[User, Depends(require_permission("persons", "update"))],
) -> AISuggestionDecisionResponse:
    """Accept edited AI content or reject it with an audit note."""
    try:
        result = await service.decide(
            person_id,
            kind=kind,
            action=data.action,
            expected_version=data.expected_version,
            user_id=current_user.id,
            value=data.value,
            selected_tags=data.selected_tags,
            note=data.note,
            audit_context=audit_context_from_request(request, current_user),
            allow_published_update=current_user.has_permission("persons", "publish"),
        )
    except AISuggestionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AISuggestionDecisionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PublishedContentChangeError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
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

    return AISuggestionDecisionResponse(
        person_id=str(result.person_id),
        kind=result.kind,
        action=result.action,
        applied_value=result.applied_value,
        accepted_tags=result.accepted_tags,
        version=result.version,
        decided_at=result.decided_at,
    )
