"""Typed results returned by AI application use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SemanticSearchResult:
    """Single result from semantic search."""

    person_id: uuid.UUID
    canonical_name: str
    slug: str
    person_type: str
    era: str | None
    summary_pl: str | None
    similarity_score: float


@dataclass
class AIStatusResult:
    """Status of AI modules."""

    embedding_provider: str
    embedding_model: str
    embedding_dimensions: int
    summary_provider: str
    total_embeddings: int
    coverage_percent: float
    last_generated_at: str | None


@dataclass
class EmbeddingResult:
    """Result of embedding generation for a person."""

    person_id: uuid.UUID
    canonical_name: str
    provider: str
    model: str
    dimensions: int
    was_updated: bool


@dataclass
class AISuggestionResult:
    """One editorial AI suggestion or actionable AI-generation task."""

    id: str
    person_id: uuid.UUID
    person_slug: str
    person_name: str
    kind: str
    status: str
    title: str
    description: str
    current_value: str | None
    suggested_value: str | None
    confidence: int
    reason: str
    action: str
    action_href: str
    updated_at: datetime


@dataclass
class AISuggestionsPageResult:
    """Filtered AI suggestions page."""

    items: list[AISuggestionResult]
    total: int
    pending_review: int
    ready_to_generate: int
    blocked: int


@dataclass
class AIFeatureStatusResult:
    """Operational state of one AI capability."""

    key: str
    label: str
    status: str
    description: str
    detail: str


@dataclass
class AIDashboardResult:
    """Admin AI centre aggregate."""

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
    last_generated_at: str | None
    feature_statuses: list[AIFeatureStatusResult]
    recent_suggestions: list[AISuggestionResult]
