"""
AI Application Service – orchestrates embedding generation, semantic search,
related saints discovery, and biography summarization.

This is the primary use-case layer that:
- Coordinates EmbeddingService + SummaryService with the DB
- Exposes typed methods for the API layer to consume
- Handles all async DB operations
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.ai_models import (
    AIDashboardResult,
    AIFeatureStatusResult,
    AISuggestionsPageResult,
)
from src.application.ai_suggestions import (
    AISuggestionBuilder,
    active_person_filter,
    has_text_expression,
    has_text_value,
    preview,
    tag_list,
)
from src.application.services.ai_vector_service import AIVectorService
from src.domain.hagiography.embedding_model import PersonEmbedding
from src.domain.hagiography.models import Person, PublicationStatus
from src.infrastructure.ai.embeddings import EmbeddingService
from src.infrastructure.ai.summarizer import SummaryService, get_summary_service

# ==============================================================================
# AI SERVICE
# ==============================================================================


class AIService(AIVectorService):
    """
    Application-level AI service.

    Instantiate with a DB session owned by the calling request or worker;
    embedding and summary services are resolved from configured singletons.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        summary_service: SummaryService | None = None,
    ) -> None:
        super().__init__(db, embedding_service)
        self._summaries = summary_service or get_summary_service()

    @property
    def summary_provider(self) -> str:
        """Return the configured summary provider identifier."""
        return self._summaries.provider_name

    # ── Summarization ───────────────────────────────────────────────────────────

    async def generate_summary(self, person_id: uuid.UUID, max_words: int = 100) -> str | None:
        """
        Generate and persist an AI summary for a person's biography.

        Args:
            person_id: UUID of the person.
            max_words: Target length of the summary in words.

        Returns:
            Generated summary string, or None if person not found.
        """
        stmt = select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        person = result.scalar_one_or_none()

        if person is None:
            return None

        biography = person.biography_pl or person.summary_pl or ""
        if not biography.strip():
            return ""

        summary = await self._summaries.summarize(biography, max_words=max_words)

        # Persist AI summary back to the person record
        person.ai_summary = summary
        await self._db.flush()

        return summary

    async def extract_person_tags(self, person_id: uuid.UUID) -> list[str]:
        """
        Extract tags from a person's biography using AI.

        Args:
            person_id: UUID of the person.

        Returns:
            List of tag strings.
        """
        stmt = select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        person = result.scalar_one_or_none()

        if person is None:
            return []

        biography = person.biography_pl or ""
        tags = await self._summaries.extract_tags(biography, person.canonical_name)

        # Persist AI tags
        person.ai_tags = tags
        await self._db.flush()

        return tags

    # ── Admin AI Centre ────────────────────────────────────────────────────────

    # Compatibility aliases preserve existing internal callers while mapping
    # suggestions is handled by a focused, deterministic builder.
    _active_person_filter = staticmethod(active_person_filter)
    _has_text_expression = staticmethod(has_text_expression)
    _has_text_value = staticmethod(has_text_value)
    _preview = staticmethod(preview)
    _tag_list = staticmethod(tag_list)

    async def list_ai_suggestions(
        self,
        *,
        kind_filter: str | None = None,
        status_filter: str | None = None,
        limit: int = 50,
    ) -> AISuggestionsPageResult:
        """Build the non-destructive editorial AI suggestions queue."""
        result = await self._db.execute(
            select(Person)
            .where(active_person_filter())
            .options(selectinload(Person.embedding))
            .order_by(Person.updated_at.desc(), Person.canonical_name.asc())
        )
        persons = result.scalars().unique().all()
        builder = AISuggestionBuilder(
            embedding_disabled=self.embedding_provider == "disabled",
            tagging_disabled=self.summary_provider == "extractive-fallback",
        )
        return builder.page(
            persons,
            kind_filter=kind_filter,
            status_filter=status_filter,
            limit=limit,
        )

    async def get_admin_dashboard(self) -> AIDashboardResult:
        """Return live AI operating metrics for the admin AI centre."""
        active_filter = self._active_person_filter()
        total_persons = (
            await self._db.execute(select(func.count(Person.id)).where(active_filter))
        ).scalar_one()
        published_persons = (
            await self._db.execute(
                select(func.count(Person.id)).where(
                    active_filter,
                    Person.status == PublicationStatus.PUBLISHED.value,
                )
            )
        ).scalar_one()
        embedding_row = (
            await self._db.execute(
                select(func.count(PersonEmbedding.id), func.max(PersonEmbedding.updated_at))
                .join(Person, Person.id == PersonEmbedding.person_id)
                .where(active_filter)
            )
        ).one()
        total_embeddings = int(embedding_row[0] or 0)
        last_generated_at = str(embedding_row[1]) if embedding_row[1] else None
        ai_summaries = (
            await self._db.execute(
                select(func.count(Person.id)).where(
                    active_filter,
                    self._has_text_expression(Person.ai_summary),
                )
            )
        ).scalar_one()
        ai_tags = (
            await self._db.execute(
                select(func.count(Person.id)).where(
                    active_filter,
                    case(
                        (
                            func.jsonb_typeof(Person.ai_tags) == "array",
                            func.jsonb_array_length(Person.ai_tags),
                        ),
                        else_=0,
                    )
                    > 0,
                )
            )
        ).scalar_one()
        suggestions = await self.list_ai_suggestions(limit=5)
        missing_embeddings = max(0, int(total_persons) - total_embeddings)
        coverage = total_embeddings / int(total_persons) * 100 if int(total_persons) else 0.0

        embedding_ready = self.embedding_provider != "disabled"
        summary_ready = self.summary_provider != "extractive-fallback"
        feature_statuses = [
            AIFeatureStatusResult(
                key="embeddings",
                label="Embeddingi",
                status="ready" if embedding_ready else "disabled",
                description="Wektory semantyczne dla profili hagiograficznych.",
                detail=(
                    f"{total_embeddings} z {int(total_persons)} aktywnych profili ma embedding."
                ),
            ),
            AIFeatureStatusResult(
                key="semantic_search",
                label="Wyszukiwanie semantyczne",
                status=(
                    "ready"
                    if embedding_ready and total_embeddings > 0
                    else "needs_data" if embedding_ready else "disabled"
                ),
                description="Wyszukiwanie po intencji i znaczeniu, nie tylko po słowach.",
                detail=(
                    "Gotowe do użycia."
                    if total_embeddings > 0
                    else "Wymaga wygenerowania pierwszych embeddingów."
                ),
            ),
            AIFeatureStatusResult(
                key="summaries",
                label="Streszczenia",
                status="ready" if summary_ready else "fallback",
                description="Robocze streszczenia biogramów do decyzji redaktora.",
                detail=(
                    f"{int(ai_summaries)} profili ma zapisane streszczenie AI."
                    if summary_ready
                    else "Działa lokalny skrót ekstrakcyjny bez zewnętrznego LLM."
                ),
            ),
            AIFeatureStatusResult(
                key="tagging",
                label="Auto-tagowanie",
                status="ready" if summary_ready else "disabled",
                description="Sugestie tagów, patronatów i tematów na podstawie biogramu.",
                detail=(
                    f"{int(ai_tags)} profili ma zapisane tagi AI."
                    if summary_ready
                    else "Wymaga dostawcy OpenAI albo Ollama."
                ),
            ),
        ]

        return AIDashboardResult(
            generated_at=datetime.now(UTC),
            embedding_provider=str(self.embedding_provider),
            embedding_model=self._embeddings.model_name,
            embedding_dimensions=self._embeddings.vector_dimensions,
            summary_provider=str(self.summary_provider),
            total_persons=int(total_persons),
            published_persons=int(published_persons),
            total_embeddings=total_embeddings,
            missing_embeddings=missing_embeddings,
            coverage_percent=round(coverage, 2),
            ai_summaries=int(ai_summaries),
            ai_tags=int(ai_tags),
            pending_suggestions=suggestions.pending_review + suggestions.ready_to_generate,
            blocked_suggestions=suggestions.blocked,
            last_generated_at=last_generated_at,
            feature_statuses=feature_statuses,
            recent_suggestions=suggestions.items,
        )
