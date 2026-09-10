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

from fastapi import APIRouter

from src.presentation.api.v1.ai.admin import (
    get_ai_dashboard,
    list_ai_suggestions,
    map_dashboard,
    map_suggestion,
)
from src.presentation.api.v1.ai.admin import router as admin_router
from src.presentation.api.v1.ai.decisions import decide_ai_suggestion
from src.presentation.api.v1.ai.decisions import router as decisions_router
from src.presentation.api.v1.ai.dependencies import (
    get_ai_service,
    get_ai_suggestion_decision_service,
    get_ai_summary_service,
    get_ai_vector_service,
)
from src.presentation.api.v1.ai.generation import (
    batch_auto_tag,
    batch_generate_embeddings,
    generate_embedding,
    generate_summary,
    generate_tags,
)
from src.presentation.api.v1.ai.generation import router as generation_router
from src.presentation.api.v1.ai.schemas import (
    AIDashboardResponse,
    AIFeatureStatusItem,
    AIStatusResponse,
    AISuggestionDecisionRequest,
    AISuggestionDecisionResponse,
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
from src.presentation.api.v1.ai.status import get_ai_status
from src.presentation.api.v1.ai.status import router as status_router

router = APIRouter()

# Private aliases remain available for internal callers that imported the former
# monolithic module directly.
_map_suggestion = map_suggestion
_map_dashboard = map_dashboard

__all__ = [
    "AIDashboardResponse",
    "AIFeatureStatusItem",
    "AISuggestionItem",
    "AISuggestionDecisionRequest",
    "AISuggestionDecisionResponse",
    "AISuggestionsResponse",
    "AIStatusResponse",
    "BatchTaskResponse",
    "EmbeddingResponse",
    "SearchResponse",
    "SearchResultItem",
    "SummaryResponse",
    "TaggingResponse",
    "batch_auto_tag",
    "batch_generate_embeddings",
    "generate_embedding",
    "generate_summary",
    "generate_tags",
    "decide_ai_suggestion",
    "get_ai_service",
    "get_ai_dashboard",
    "get_ai_status",
    "get_ai_summary_service",
    "get_ai_suggestion_decision_service",
    "get_ai_vector_service",
    "get_related",
    "list_ai_suggestions",
    "map_dashboard",
    "map_suggestion",
    "semantic_search",
]
router.include_router(status_router)
router.include_router(admin_router)
router.include_router(generation_router)
router.include_router(search_router)
router.include_router(decisions_router)
