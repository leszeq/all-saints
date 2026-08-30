"""Protected editorial dashboard and review queue endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.editorial_service import (
    EditorialAuthorizationError,
    EditorialNotFoundError,
    EditorialService,
    EditorialTransitionError,
)
from src.application.services.person_service import PersonVersionConflictError
from src.domain.hagiography.models import PublicationStatus
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import get_current_user, require_permission
from src.presentation.api.v1.editorial.schemas import (
    EditorialDashboardSchema,
    EditorialPriority,
    EditorialQualityReportSchema,
    EditorialQueueResponseSchema,
    EditorialTransitionResponseSchema,
    EditorialTransitionSchema,
)

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=EditorialDashboardSchema,
    summary="Get live editorial dashboard metrics",
)
async def get_editorial_dashboard(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> EditorialDashboardSchema:
    return await EditorialService(db).dashboard()


@router.get(
    "/quality",
    response_model=EditorialQualityReportSchema,
    summary="Get data quality centre report",
)
async def get_data_quality_report(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> EditorialQualityReportSchema:
    return await EditorialService(db).quality_report()


@router.get(
    "/queue",
    response_model=EditorialQueueResponseSchema,
    summary="List the editorial review queue",
)
async def list_editorial_queue(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(None, max_length=200),
    status_filter: PublicationStatus | None = Query(None, alias="status"),
    priority: EditorialPriority | None = None,
    attention: bool = Query(False, description="Show only records requiring editorial attention"),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> EditorialQueueResponseSchema:
    if status_filter not in {None, PublicationStatus.DRAFT, PublicationStatus.REVIEW}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Kolejka obsługuje statusy draft i review",
        )
    return await EditorialService(db).list_queue(
        page=page,
        per_page=per_page,
        search=search,
        status_filter=status_filter,
        priority_filter=priority,
        attention_only=attention,
    )


@router.post(
    "/queue/{person_id}/transition",
    response_model=EditorialTransitionResponseSchema,
    summary="Move a person through the editorial workflow",
)
async def transition_editorial_record(
    person_id: uuid.UUID,
    data: EditorialTransitionSchema,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EditorialTransitionResponseSchema:
    try:
        return await EditorialService(db).transition(
            person_id,
            data.target_status,
            user_id=current_user.id,
            note=data.note,
            granted_permissions=current_user.get_permissions(),
            expected_version=data.expected_version,
        )
    except EditorialAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except EditorialNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EditorialTransitionError as exc:
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
