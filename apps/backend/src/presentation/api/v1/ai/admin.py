"""Protected AI dashboard and editorial suggestions queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.ai_models import AIDashboardResult, AISuggestionResult
from src.application.ai_service import AIService
from src.domain.identity.models import User
from src.presentation.api.v1.ai.dependencies import get_ai_service
from src.presentation.api.v1.ai.schemas import (
    AIDashboardResponse,
    AIFeatureStatusItem,
    AISuggestionItem,
    AISuggestionsResponse,
)
from src.presentation.api.v1.auth.router import require_permission

router = APIRouter()


def map_suggestion(item: AISuggestionResult) -> AISuggestionItem:
    """Convert a service-layer suggestion into its transport schema."""
    return AISuggestionItem(
        id=item.id,
        person_id=str(item.person_id),
        person_slug=item.person_slug,
        person_name=item.person_name,
        person_version=item.person_version,
        kind=item.kind,
        status=item.status,
        title=item.title,
        description=item.description,
        current_value=item.current_value,
        suggested_value=item.suggested_value,
        confidence=item.confidence,
        reason=item.reason,
        action=item.action,
        action_href=item.action_href,
        updated_at=item.updated_at,
    )


def map_dashboard(result: AIDashboardResult) -> AIDashboardResponse:
    """Convert the AI centre aggregate into its transport schema."""
    return AIDashboardResponse(
        generated_at=result.generated_at,
        embedding_provider=result.embedding_provider,
        embedding_model=result.embedding_model,
        embedding_dimensions=result.embedding_dimensions,
        summary_provider=result.summary_provider,
        total_persons=result.total_persons,
        published_persons=result.published_persons,
        total_embeddings=result.total_embeddings,
        missing_embeddings=result.missing_embeddings,
        coverage_percent=result.coverage_percent,
        ai_summaries=result.ai_summaries,
        ai_tags=result.ai_tags,
        pending_suggestions=result.pending_suggestions,
        blocked_suggestions=result.blocked_suggestions,
        last_generated_at=result.last_generated_at,
        feature_statuses=[
            AIFeatureStatusItem(
                key=item.key,
                label=item.label,
                status=item.status,
                description=item.description,
                detail=item.detail,
            )
            for item in result.feature_statuses
        ],
        recent_suggestions=[map_suggestion(item) for item in result.recent_suggestions],
    )


@router.get(
    "/dashboard",
    response_model=AIDashboardResponse,
    summary="Admin AI Centre",
    description="Returns live AI coverage, provider state and recent editorial AI tasks.",
)
async def get_ai_dashboard(
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _user: Annotated[User, Depends(require_permission("persons", "read"))],
) -> AIDashboardResponse:
    """Get operational AI metrics for the admin panel."""
    return map_dashboard(await ai_service.get_admin_dashboard())


@router.get(
    "/suggestions",
    response_model=AISuggestionsResponse,
    summary="AI Suggestions Queue",
    description=(
        "Lists AI-generated proposals and AI-generation tasks for editorial review. "
        "Suggestions never overwrite approved editorial content automatically."
    ),
)
async def list_ai_suggestions(
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _user: Annotated[User, Depends(require_permission("persons", "read"))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    kind: Annotated[
        str | None,
        Query(pattern="^(embedding|summary|tags)$"),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern="^(pending_review|ready_to_generate|blocked)$"),
    ] = None,
) -> AISuggestionsResponse:
    """List actionable AI suggestions and generation tasks."""
    result = await ai_service.list_ai_suggestions(
        kind_filter=kind,
        status_filter=status_filter,
        limit=limit,
    )
    return AISuggestionsResponse(
        items=[map_suggestion(item) for item in result.items],
        total=result.total,
        pending_review=result.pending_review,
        ready_to_generate=result.ready_to_generate,
        blocked=result.blocked,
    )
