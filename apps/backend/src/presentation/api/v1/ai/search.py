"""Public semantic search and related-person endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.application.ai_models import SemanticSearchResult
from src.application.ai_service import AIService
from src.infrastructure.ai.embeddings import EmbeddingUnavailableError
from src.presentation.api.v1.ai.dependencies import get_ai_service
from src.presentation.api.v1.ai.schemas import SearchResponse, SearchResultItem

router = APIRouter()


def _search_response(
    *,
    query: str,
    results: list[SemanticSearchResult],
    provider: str,
) -> SearchResponse:
    return SearchResponse(
        query=query,
        results=[
            SearchResultItem(
                person_id=str(result.person_id),
                canonical_name=result.canonical_name,
                slug=result.slug,
                person_type=result.person_type,
                era=result.era,
                summary_pl=result.summary_pl,
                similarity_score=result.similarity_score,
            )
            for result in results
        ],
        total=len(results),
        provider=provider,
    )


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic Search",
    description=(
        "Search for saints/blessed using natural language queries. "
        "Uses vector cosine similarity against pgvector embeddings. "
        "Examples: 'patron zwierząt', 'misjonarz w Azji', 'święta od spraw beznadziejnych'"
    ),
)
async def semantic_search(
    q: Annotated[str, Query(min_length=2, max_length=500, description="Search query")],
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    person_type: Annotated[str | None, Query(description="Filter by person type")] = None,
    era: Annotated[str | None, Query(description="Filter by era")] = None,
) -> SearchResponse:
    """Perform semantic similarity search over published persons."""
    try:
        results = await ai_service.semantic_search(
            query=q,
            limit=limit,
            person_type=person_type,
            era=era,
        )
    except EmbeddingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return _search_response(
        query=q,
        results=results,
        provider=ai_service.embedding_provider,
    )


@router.get(
    "/related/{person_id}",
    response_model=SearchResponse,
    summary="Related Saints",
    description=(
        "Find saints/blessed most similar to the given person based on their embedding vector. "
        "Useful for 'You might also be interested in' sections."
    ),
)
async def get_related(
    person_id: uuid.UUID,
    ai_service: Annotated[AIService, Depends(get_ai_service)],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> SearchResponse:
    """Find similar persons to the given person by embedding similarity."""
    try:
        results = await ai_service.find_related(person_id=person_id, limit=limit)
    except EmbeddingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return _search_response(
        query=f"related:{person_id}",
        results=results,
        provider=ai_service.embedding_provider,
    )
