"""Protected AI generation and batch-dispatch endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from src.application.services.ai_summary_service import AISummaryService
from src.application.services.ai_vector_service import AIVectorService
from src.domain.identity.models import User
from src.infrastructure.ai.embeddings import EmbeddingUnavailableError
from src.infrastructure.ai.summarizer import TaggingUnavailableError
from src.presentation.api.v1.ai.dependencies import (
    get_ai_summary_service,
    get_ai_vector_service,
)
from src.presentation.api.v1.ai.schemas import (
    BatchTaskResponse,
    EmbeddingResponse,
    SummaryResponse,
    TaggingResponse,
)
from src.presentation.api.v1.auth.router import require_permission

router = APIRouter()


@router.post(
    "/embeddings/{person_id}",
    response_model=EmbeddingResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Person Embedding",
    description="Generate or refresh the semantic vector embedding for a specific person.",
)
async def generate_embedding(
    person_id: uuid.UUID,
    ai_service: Annotated[AIVectorService, Depends(get_ai_vector_service)],
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
    ai_service: Annotated[AISummaryService, Depends(get_ai_summary_service)],
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
    ai_service: Annotated[AISummaryService, Depends(get_ai_summary_service)],
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
    ai_service: Annotated[AIVectorService, Depends(get_ai_vector_service)],
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
    ai_service: Annotated[AISummaryService, Depends(get_ai_summary_service)],
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
