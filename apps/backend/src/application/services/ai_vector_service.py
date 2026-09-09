"""Embedding generation and semantic person search use cases."""

from __future__ import annotations

import math
import uuid
from typing import Protocol, cast

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai_models import AIStatusResult, EmbeddingResult, SemanticSearchResult
from src.domain.hagiography.embedding_model import PersonEmbedding
from src.domain.hagiography.models import Person, PublicationStatus
from src.infrastructure.ai.embeddings import (
    EmbeddingService,
    build_person_embedding_text,
    get_embedding_service,
)


class _SemanticSearchRow(Protocol):
    person_id: uuid.UUID
    canonical_name: str
    slug: str
    person_type: str
    era: str | None
    summary_pl: str | None
    similarity_score: float


class AIVectorService:
    """Generate person vectors and execute semantic similarity queries."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._db = db
        self._embeddings = embedding_service or get_embedding_service()

    @property
    def embedding_provider(self) -> str:
        """Return the configured embedding provider identifier."""
        return self._embeddings.provider_name

    @property
    def summary_provider(self) -> str:
        """Return a fallback name when no summary capability is composed."""
        return "unavailable"

    async def generate_person_embedding(self, person_id: uuid.UUID) -> EmbeddingResult | None:
        """Generate or refresh the embedding for one active person."""
        result = await self._db.execute(
            select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        )
        person = result.scalar_one_or_none()
        if person is None:
            logger.warning(f"Person {person_id} not found for embedding generation")
            return None

        source_text = build_person_embedding_text(
            canonical_name=person.canonical_name,
            biography=person.biography_pl,
            summary=person.summary_pl,
            era=person.era,
        )
        vector = await self._embeddings.embed(source_text)

        existing_result = await self._db.execute(
            select(PersonEmbedding).where(PersonEmbedding.person_id == person_id)
        )
        existing = existing_result.scalar_one_or_none()
        was_updated = existing is not None
        if existing:
            existing.embedding = vector
            existing.source_text = source_text
            existing.provider = self._embeddings.provider_name
            existing.model = self._embeddings.model_name
        else:
            self._db.add(
                PersonEmbedding(
                    person_id=person_id,
                    embedding=vector,
                    source_text=source_text,
                    provider=self._embeddings.provider_name,
                    model=self._embeddings.model_name,
                )
            )

        await self._db.flush()
        logger.info(
            f"Prepared {'updated' if was_updated else 'new'} embedding "
            f"for {person.canonical_name}"
        )
        return EmbeddingResult(
            person_id=person.id,
            canonical_name=person.canonical_name,
            provider=self._embeddings.provider_name,
            model=self._embeddings.model_name,
            dimensions=self._embeddings.vector_dimensions,
            was_updated=was_updated,
        )

    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        person_type: str | None = None,
        era: str | None = None,
    ) -> list[SemanticSearchResult]:
        """Find published persons nearest to a natural-language query."""
        query_vector = await self._embeddings.embed(query)
        vector_str = "[" + ",".join(str(value) for value in query_vector) + "]"
        where_clauses = [
            "p.deleted_at IS NULL",
            "p.status = 'published'",
            "pe.embedding IS NOT NULL",
        ]
        params: dict[str, object] = {"query_vector": vector_str, "limit": limit}
        if person_type:
            where_clauses.append("p.person_type = :person_type")
            params["person_type"] = person_type
        if era:
            where_clauses.append("p.era = :era")
            params["era"] = era

        statement = text(f"""
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
            WHERE {" AND ".join(where_clauses)}
              AND vector_norm(pe.embedding) > 0
            ORDER BY pe.embedding <=> CAST(:query_vector AS vector)
            LIMIT :limit
        """)
        try:
            result = await self._db.execute(statement, params)
            rows = result.fetchall()
        except Exception as exc:
            logger.error(f"Semantic search failed: {exc}")
            raise
        return [self._map_search_result(cast(_SemanticSearchRow, row)) for row in rows]

    async def find_related(
        self,
        person_id: uuid.UUID,
        limit: int = 5,
    ) -> list[SemanticSearchResult]:
        """Find published persons nearest to one person's stored embedding."""
        result = await self._db.execute(
            select(PersonEmbedding)
            .join(Person, Person.id == PersonEmbedding.person_id)
            .where(
                PersonEmbedding.person_id == person_id,
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
            )
        )
        reference = result.scalar_one_or_none()
        if reference is None:
            logger.info(f"No embedding for person {person_id} – returning empty related list")
            return []

        values = list(reference.embedding) if reference.embedding is not None else []
        if (
            not values
            or not all(math.isfinite(float(value)) for value in values)
            or not any(float(value) != 0.0 for value in values)
        ):
            logger.warning(f"Invalid or zero embedding for person {person_id}")
            return []

        statement = text("""
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
        params = {
            "ref_vector": "[" + ",".join(str(value) for value in values) + "]",
            "exclude_id": person_id,
            "limit": limit,
        }
        try:
            result = await self._db.execute(statement, params)
            rows = result.fetchall()
        except Exception as exc:
            logger.error(f"Related search failed: {exc}")
            raise
        return [self._map_search_result(cast(_SemanticSearchRow, row)) for row in rows]

    async def get_status(self) -> AIStatusResult:
        """Return vector provider details and current embedding coverage."""
        total_result = await self._db.execute(
            text("SELECT COUNT(*) FROM persons WHERE deleted_at IS NULL")
        )
        total_persons = total_result.scalar() or 0
        embedding_result = await self._db.execute(text("""
            SELECT COUNT(*), MAX(pe.updated_at)
            FROM person_embeddings pe
            INNER JOIN persons p ON p.id = pe.person_id
            WHERE p.deleted_at IS NULL
              AND vector_norm(pe.embedding) > 0
        """))
        row = embedding_result.fetchone()
        total_embeddings = row[0] if row else 0
        last_generated_at = str(row[1]) if row and row[1] else None
        coverage = total_embeddings / total_persons * 100 if total_persons else 0.0
        return AIStatusResult(
            embedding_provider=self.embedding_provider,
            embedding_model=self._embeddings.model_name,
            embedding_dimensions=self._embeddings.vector_dimensions,
            summary_provider=self.summary_provider,
            total_embeddings=int(total_embeddings),
            coverage_percent=round(coverage, 2),
            last_generated_at=last_generated_at,
        )

    @staticmethod
    def _map_search_result(row: _SemanticSearchRow) -> SemanticSearchResult:
        return SemanticSearchResult(
            person_id=row.person_id,
            canonical_name=row.canonical_name,
            slug=row.slug,
            person_type=row.person_type,
            era=row.era,
            summary_pl=row.summary_pl,
            similarity_score=float(row.similarity_score),
        )
