"""Transport schemas for AI status, search, suggestions, and generation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AIStatusResponse(BaseModel):
    """AI module status response."""

    embedding_provider: str = Field(description="Active embedding provider name")
    embedding_model: str = Field(description="Embedding model name")
    embedding_dimensions: int = Field(description="Vector dimensionality")
    summary_provider: str = Field(description="Active summarization provider name")
    total_embeddings: int = Field(description="Total person embeddings stored")
    coverage_percent: float = Field(description="Percentage of persons with embeddings")
    last_generated_at: str | None = Field(None, description="ISO timestamp of last embedding")


class EmbeddingResponse(BaseModel):
    """Embedding generation result."""

    person_id: str
    canonical_name: str
    provider: str
    model: str
    dimensions: int
    was_updated: bool
    message: str


class SearchResultItem(BaseModel):
    """Single semantic search result."""

    person_id: str
    canonical_name: str
    slug: str
    person_type: str
    era: str | None = None
    summary_pl: str | None = None
    similarity_score: float = Field(ge=-1.0, le=1.0, description="Cosine similarity (-1–1)")


class SearchResponse(BaseModel):
    """Semantic search response."""

    query: str
    results: list[SearchResultItem]
    total: int
    provider: str


class SummaryResponse(BaseModel):
    """Biography summary response."""

    person_id: str
    summary: str
    word_count: int
    provider: str


class BatchTaskResponse(BaseModel):
    """Background task dispatch response."""

    task_id: str
    message: str
    status: str = "queued"


class TaggingResponse(BaseModel):
    """AI tag extraction result."""

    person_id: str
    tags: list[str]
    total: int
    provider: str


class AISuggestionItem(BaseModel):
    """One editorial AI suggestion or generation task."""

    id: str
    person_id: str
    person_slug: str
    person_name: str
    kind: str = Field(description="embedding, summary or tags")
    status: str = Field(description="pending_review, ready_to_generate or blocked")
    title: str
    description: str
    current_value: str | None = None
    suggested_value: str | None = None
    confidence: int = Field(ge=0, le=100)
    reason: str
    action: str
    action_href: str
    updated_at: datetime


class AISuggestionsResponse(BaseModel):
    """Paginated-ish AI suggestions queue response."""

    items: list[AISuggestionItem]
    total: int
    pending_review: int
    ready_to_generate: int
    blocked: int


class AIFeatureStatusItem(BaseModel):
    """Operational state of one AI capability."""

    key: str
    label: str
    status: str
    description: str
    detail: str


class AIDashboardResponse(BaseModel):
    """Admin AI centre dashboard response."""

    generated_at: datetime
    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    summary_provider: str
    total_persons: int
    published_persons: int
    total_embeddings: int
    missing_embeddings: int
    coverage_percent: float
    ai_summaries: int
    ai_tags: int
    pending_suggestions: int
    blocked_suggestions: int
    last_generated_at: str | None = None
    feature_statuses: list[AIFeatureStatusItem]
    recent_suggestions: list[AISuggestionItem]
