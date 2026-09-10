"""Public operational status for the AI module."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.application.ai_service import AIService
from src.presentation.api.v1.ai.dependencies import get_ai_service
from src.presentation.api.v1.ai.schemas import AIStatusResponse

router = APIRouter()


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
