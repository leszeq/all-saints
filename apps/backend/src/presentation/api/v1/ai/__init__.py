"""
AI API Router – /api/v1/ai

Endpoints:
- GET  /status          – AI module status and coverage
- GET  /dashboard       – Admin AI centre metrics
- GET  /suggestions     – Editorial AI suggestions queue
- POST /embeddings/{id} – Generate/refresh embedding for a person
- GET  /search          – Semantic search over person embeddings
- GET  /related/{id}    – Find similar persons by embedding
- POST /summarize/{id}  – Generate AI biography summary
- POST /tag/{id}        – Generate AI tag suggestions for a person
- POST /batch/embed     – Trigger bulk embedding generation (admin only)
- POST /batch/tag       – Trigger bulk auto-tagging (admin only)
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from src.application.ai_models import AIDashboardResult, AISuggestionResult
from src.application.ai_service import AIService
from src.domain.identity.models import User
from src.infrastructure.ai.embeddings import EmbeddingUnavailableError
from src.infrastructure.ai.summarizer import TaggingUnavailableError
from src.presentation.api.v1.ai.dependencies import get_ai_service
from src.presentation.api.v1.ai.schemas import (
    AIDashboardResponse,
    AIFeatureStatusItem,
    AIStatusResponse,
    AISuggestionItem,
    AISuggestionsResponse,
    BatchTaskResponse,
    EmbeddingResponse,
    SearchResponse,
    SearchResultItem,
    SummaryResponse,
    TaggingResponse,
)
from src.presentation.api.v1.ai.search import get_related, semantic_search
from src.presentation.api.v1.ai.search import router as search_router
from src.presentation.api.v1.auth.router import require_permission

router = APIRouter()

__all__ = [
    "AIDashboardResponse",
    "AIFeatureStatusItem",
    "AISuggestionItem",
    "AISuggestionsResponse",
    "AIStatusResponse",
    "BatchTaskResponse",
    "EmbeddingResponse",
    "SearchResponse",
    "SearchResultItem",
    "SummaryResponse",
    "TaggingResponse",
    "get_ai_service",
    "get_related",
    "semantic_search",
]


def _map_suggestion(item: AISuggestionResult) -> AISuggestionItem:
    """Convert service-layer suggestion dataclass into an API schema."""
    return AISuggestionItem(
        id=item.id,
        person_id=str(item.person_id),
        person_slug=item.person_slug,
        person_name=item.person_name,
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


def _map_dashboard(result: AIDashboardResult) -> AIDashboardResponse:
    """Convert service-layer dashboard dataclass into an API schema."""
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
        recent_suggestions=[_map_suggestion(item) for item in result.recent_suggestions],
    )


# ==============================================================================
# ENDPOINTS
# ==============================================================================


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
    return _map_dashboard(await ai_service.get_admin_dashboard())


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
        items=[_map_suggestion(item) for item in result.items],
        total=result.total,
        pending_review=result.pending_review,
        ready_to_generate=result.ready_to_generate,
        blocked=result.blocked,
    )


@router.get(
    "/status",
    response_model=AIStatusResponse,
    summary="AI Module Status",
    description="Returns current AI provider configuration and embedding coverage statistics.",
)
async def get_ai_status(
    ai_service: Annotated[AIService, Depends(get_ai_service)],
) -> AIStatusResponse:
    """Get AI module status and statistics."""
    result = await ai_service.get_status()
    return AIStatusResponse(
        embedding_provider=result.embedding_provider,
        embedding_model=result.embedding_model,
        embedding_dimensions=result.embedding_dimensions,
        summary_provider=result.summary_provider,
        total_embeddings=result.total_embeddings,
        coverage_percent=result.coverage_percent,
        last_generated_at=result.last_generated_at,
    )


@router.post(
    "/embeddings/{person_id}",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Person Embedding",
    description="Generate or refresh the semantic vector embedding for a specific person.",
)
async def generate_embedding(
    person_id: uuid.UUID,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _user: Annotated[User, Depends(require_permission("persons", "update"))],
) -> EmbeddingResponse:
    """Generate or refresh embedding for a single person."""
    try:
        result = await ai_service.generate_person_embedding(person_id)
    except EmbeddingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person with id {person_id} not found",
        )

    return EmbeddingResponse(
        person_id=str(result.person_id),
        canonical_name=result.canonical_name,
        provider=result.provider,
        model=result.model,
        dimensions=result.dimensions,
        was_updated=result.was_updated,
        message="Embedding updated" if result.was_updated else "Embedding created",
    )


router.include_router(search_router)


@router.post(
    "/summarize/{person_id}",
    response_model=SummaryResponse,
    summary="Generate Biography Summary",
    description=(
        "Generate a concise AI summary of a person's biography. "
        "The summary is persisted to the person record for future retrieval."
    ),
)
async def generate_summary(
    person_id: uuid.UUID,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _user: Annotated[User, Depends(require_permission("persons", "update"))],
    max_words: Annotated[int, Query(ge=20, le=500)] = 100,
) -> SummaryResponse:
    """Generate or regenerate an AI biography summary."""
    summary = await ai_service.generate_summary(person_id, max_words=max_words)

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Person with id {person_id} not found",
        )

    return SummaryResponse(
        person_id=str(person_id),
        summary=summary,
        word_count=len(summary.split()) if summary else 0,
        provider=ai_service.summary_provider,
    )


@router.post(
    "/tag/{person_id}",
    response_model=TaggingResponse,
    summary="Generate Person Tag Suggestions",
    description=(
        "Generate AI tag suggestions for a single person. "
        "The suggestions are stored in ai_tags and must be reviewed by an editor."
    ),
)
async def generate_tags(
    person_id: uuid.UUID,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    _user: Annotated[User, Depends(require_permission("persons", "update"))],
) -> TaggingResponse:
    """Generate or regenerate AI tag suggestions for a single person."""
    try:
        tags = await ai_service.extract_person_tags(person_id)
    except TaggingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return TaggingResponse(
        person_id=str(person_id),
        tags=tags,
        total=len(tags),
        provider=ai_service.summary_provider,
    )


@router.post(
    "/batch/embed",
    response_model=BatchTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Generate Embeddings",
    description=(
        "Dispatch a background Celery task to generate embeddings for all persons. "
        "Returns immediately with a task ID for status polling."
    ),
)
async def batch_generate_embeddings(
    _user: Annotated[User, Depends(require_permission("persons", "publish"))],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    overwrite_existing: Annotated[
        bool, Query(description="Regenerate existing embeddings")
    ] = False,
    batch_size: Annotated[int, Query(ge=10, le=500)] = 50,
) -> BatchTaskResponse:
    """Trigger bulk embedding generation as a background Celery task."""
    if ai_service.embedding_provider == "disabled":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Moduł embeddingów jest wyłączony",
        )

    try:
        from src.workers.tasks.ai import batch_generate_embeddings as celery_task

        task = celery_task.delay(
            batch_size=batch_size,
            overwrite_existing=overwrite_existing,
        )
        return BatchTaskResponse(
            task_id=task.id,
            message=f"Batch embedding job dispatched (overwrite={overwrite_existing})",
        )
    except Exception as exc:
        logger.exception("Could not dispatch batch embedding job")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nie udało się uruchomić zadania generowania embeddingów",
        ) from exc


@router.post(
    "/batch/tag",
    response_model=BatchTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Auto-Tag Persons",
    description="Dispatch a background task to auto-tag all persons using AI.",
)
async def batch_auto_tag(
    _user: Annotated[User, Depends(require_permission("persons", "publish"))],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    only_untagged: Annotated[bool, Query(description="Only process persons without tags")] = True,
) -> BatchTaskResponse:
    """Trigger bulk auto-tagging as a background Celery task."""
    if ai_service.summary_provider == "extractive-fallback":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Automatyczne tagowanie AI jest wyłączone",
        )

    try:
        from src.workers.tasks.ai import batch_auto_tag as celery_task

        task = celery_task.delay(only_untagged=only_untagged)
        return BatchTaskResponse(
            task_id=task.id,
            message=f"Auto-tag job dispatched (only_untagged={only_untagged})",
        )
    except Exception as exc:
        logger.exception("Could not dispatch batch auto-tag job")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nie udało się uruchomić zadania automatycznego tagowania",
        ) from exc
