"""
AI Application Service – orchestrates embedding generation, semantic search,
related saints discovery, and biography summarization.

This is the primary use-case layer that:
- Coordinates EmbeddingService + SummaryService with the DB
- Exposes typed methods for the API layer to consume
- Handles all async DB operations
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.ai_models import (
    AIDashboardResult,
    AIFeatureStatusResult,
    AIStatusResult,
    AISuggestionsPageResult,
    EmbeddingResult,
    SemanticSearchResult,
)
from src.application.ai_suggestions import (
    AISuggestionBuilder,
    active_person_filter,
    has_text_expression,
    has_text_value,
    preview,
    tag_list,
)
from src.domain.hagiography.embedding_model import PersonEmbedding
from src.domain.hagiography.models import Person, PublicationStatus
from src.infrastructure.ai.embeddings import (
    EmbeddingService,
    build_person_embedding_text,
    get_embedding_service,
)
from src.infrastructure.ai.summarizer import SummaryService, get_summary_service

# ==============================================================================
# AI SERVICE
# ==============================================================================


class AIService:
    """
    Application-level AI service.

    Instantiate with a DB session; embedding and summary services are
    resolved from singletons (configured once at startup).
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
        summary_service: SummaryService | None = None,
    ) -> None:
        self._db = db
        self._embeddings = embedding_service or get_embedding_service()
        self._summaries = summary_service or get_summary_service()

    @property
    def embedding_provider(self) -> str:
        """Return the configured embedding provider identifier."""
        return self._embeddings.provider_name

    @property
    def summary_provider(self) -> str:
        """Return the configured summary provider identifier."""
        return self._summaries.provider_name

    # ── Embedding Generation ────────────────────────────────────────────────────

    async def generate_person_embedding(self, person_id: uuid.UUID) -> EmbeddingResult | None:
        """
        Generate or refresh the embedding for a single person.

        Args:
            person_id: UUID of the person to embed.

        Returns:
            EmbeddingResult with metadata, or None if person not found.
        """
        # Load person with related data for rich embedding text
        stmt = (
            select(Person)
            .where(Person.id == person_id, Person.deleted_at.is_(None))
            .options(
                # Load patronages, tags, categories, occupations for richer text
            )
        )
        result = await self._db.execute(stmt)
        person = result.scalar_one_or_none()

        if person is None:
            logger.warning(f"Person {person_id} not found for embedding generation")
            return None

        # Build the embedding source text
        source_text = build_person_embedding_text(
            canonical_name=person.canonical_name,
            biography=person.biography_pl,
            summary=person.summary_pl,
            era=person.era,
        )

        # Generate vector
        vector = await self._embeddings.embed(source_text)

        # Upsert PersonEmbedding
        existing_stmt = select(PersonEmbedding).where(PersonEmbedding.person_id == person_id)
        existing_result = await self._db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        was_updated = existing is not None

        if existing:
            existing.embedding = vector
            existing.source_text = source_text
            existing.provider = self._embeddings.provider_name
            existing.model = self._embeddings.model_name
        else:
            new_embedding = PersonEmbedding(
                person_id=person_id,
                embedding=vector,
                source_text=source_text,
                provider=self._embeddings.provider_name,
                model=self._embeddings.model_name,
            )
            self._db.add(new_embedding)

        await self._db.commit()
        logger.info(
            f"{'Updated' if was_updated else 'Created'} embedding for {person.canonical_name}"
        )

        return EmbeddingResult(
            person_id=person.id,
            canonical_name=person.canonical_name,
            provider=self._embeddings.provider_name,
            model=self._embeddings.model_name,
            dimensions=self._embeddings.vector_dimensions,
            was_updated=was_updated,
        )

    # ── Semantic Search ─────────────────────────────────────────────────────────

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        person_type: str | None = None,
        era: str | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Semantic similarity search over person embeddings.

        Uses cosine distance (pgvector) to find persons whose embedding
        is closest to the query embedding.

        Args:
            query: Natural language search query (e.g. "patron zwierząt").
            limit: Maximum number of results to return.
            person_type: Optional filter by PersonType enum value.
            era: Optional filter by era.

        Returns:
            List of SemanticSearchResult sorted by similarity (desc).
        """
        # Embed the query
        query_vector = await self._embeddings.embed(query)

        # Format as PostgreSQL array literal
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        # Build the SQL query using pgvector cosine distance operator (<=>)
        # 1 - cosine_distance gives us cosine similarity (higher = more similar)
        where_clauses = [
            "p.deleted_at IS NULL",
            "p.status = 'published'",
            "pe.embedding IS NOT NULL",
        ]
        params: dict[str, Any] = {
            "query_vector": vector_str,
            "limit": limit,
        }

        if person_type:
            where_clauses.append("p.person_type = :person_type")
            params["person_type"] = person_type

        if era:
            where_clauses.append("p.era = :era")
            params["era"] = era

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT
                p.id AS person_id,
                p.canonical_name,
                p.slug,
                p.person_type,
                p.era,
                p.summary_pl,
                GREATEST(
                    -1.0,
                    LEAST(1.0, 1 - (pe.embedding <=> CAST(:query_vector AS vector)))
                ) AS similarity_score
            FROM persons p
            INNER JOIN person_embeddings pe ON pe.person_id = p.id
            WHERE {where_sql}
              AND vector_norm(pe.embedding) > 0
            ORDER BY pe.embedding <=> CAST(:query_vector AS vector)
            LIMIT :limit
        """)

        try:
            result = await self._db.execute(sql, params)
            rows = result.fetchall()
        except Exception as exc:
            logger.error(f"Semantic search failed: {exc}")
            raise

        return [
            SemanticSearchResult(
                person_id=row.person_id,
                canonical_name=row.canonical_name,
                slug=row.slug,
                person_type=row.person_type,
                era=row.era,
                summary_pl=row.summary_pl,
                similarity_score=float(row.similarity_score),
            )
            for row in rows
        ]

    # ── Related Saints ──────────────────────────────────────────────────────────

    async def find_related(
        self,
        person_id: uuid.UUID,
        limit: int = 5,
    ) -> list[SemanticSearchResult]:
        """
        Find saints/blessed similar to the given person via embedding similarity.

        Args:
            person_id: UUID of the reference person.
            limit: Number of similar persons to return.

        Returns:
            List of similar persons sorted by similarity (desc).
        """
        # Load the reference person's embedding
        stmt = (
            select(PersonEmbedding)
            .join(Person, Person.id == PersonEmbedding.person_id)
            .where(
                PersonEmbedding.person_id == person_id,
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
            )
        )
        result = await self._db.execute(stmt)
        ref_embedding = result.scalar_one_or_none()

        if ref_embedding is None:
            logger.info(f"No embedding for person {person_id} – returning empty related list")
            return []

        raw_embedding = ref_embedding.embedding
        embedding_values = list(raw_embedding) if raw_embedding is not None else []
        if (
            not embedding_values
            or not all(math.isfinite(float(value)) for value in embedding_values)
            or not any(float(value) != 0.0 for value in embedding_values)
        ):
            logger.warning(f"Invalid or zero embedding for person {person_id}")
            return []

        vector_str = "[" + ",".join(str(v) for v in embedding_values) + "]"

        sql = text("""
            SELECT
                p.id AS person_id,
                p.canonical_name,
                p.slug,
                p.person_type,
                p.era,
                p.summary_pl,
                GREATEST(
                    -1.0,
                    LEAST(1.0, 1 - (pe.embedding <=> CAST(:ref_vector AS vector)))
                ) AS similarity_score
            FROM persons p
            INNER JOIN person_embeddings pe ON pe.person_id = p.id
            WHERE p.deleted_at IS NULL
              AND p.status = 'published'
              AND pe.person_id != :exclude_id
              AND pe.embedding IS NOT NULL
              AND vector_norm(pe.embedding) > 0
            ORDER BY pe.embedding <=> CAST(:ref_vector AS vector)
            LIMIT :limit
        """)

        try:
            result = await self._db.execute(
                sql,
                {"ref_vector": vector_str, "exclude_id": person_id, "limit": limit},
            )
            rows = result.fetchall()
        except Exception as exc:
            logger.error(f"Related search failed: {exc}")
            raise

        return [
            SemanticSearchResult(
                person_id=row.person_id,
                canonical_name=row.canonical_name,
                slug=row.slug,
                person_type=row.person_type,
                era=row.era,
                summary_pl=row.summary_pl,
                similarity_score=float(row.similarity_score),
            )
            for row in rows
        ]

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
        await self._db.commit()

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
        await self._db.commit()

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
                    else "needs_data"
                    if embedding_ready
                    else "disabled"
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

    # ── Status ──────────────────────────────────────────────────────────────────

    async def get_status(self) -> AIStatusResult:
        """
        Get the current status of AI modules.

        Returns embedding provider info and coverage statistics.
        """
        # Count total persons
        total_sql = text("SELECT COUNT(*) FROM persons WHERE deleted_at IS NULL")
        total_result = await self._db.execute(total_sql)
        total_persons = total_result.scalar() or 0

        # Count embeddings
        emb_sql = text("""
            SELECT COUNT(*), MAX(pe.updated_at)
            FROM person_embeddings pe
            INNER JOIN persons p ON p.id = pe.person_id
            WHERE p.deleted_at IS NULL
              AND vector_norm(pe.embedding) > 0
        """)
        emb_result = await self._db.execute(emb_sql)
        emb_row = emb_result.fetchone()
        total_embeddings = emb_row[0] if emb_row else 0
        last_generated_at = str(emb_row[1]) if emb_row and emb_row[1] else None

        coverage = (total_embeddings / total_persons * 100) if total_persons > 0 else 0.0

        return AIStatusResult(
            embedding_provider=self.embedding_provider,
            embedding_model=self._embeddings.model_name,
            embedding_dimensions=self._embeddings.vector_dimensions,
            summary_provider=self.summary_provider,
            total_embeddings=int(total_embeddings),
            coverage_percent=round(coverage, 2),
            last_generated_at=last_generated_at,
        )
