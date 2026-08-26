"""Regression tests for the semantic AI module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from alembic.config import Config
from alembic.script import ScriptDirectory
from src.application.ai_service import AIService
from src.infrastructure.ai.embeddings import (
    VECTOR_DIM,
    BaseEmbeddingProvider,
    DisabledEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingService,
    EmbeddingUnavailableError,
    build_embedding_provider,
)
from src.infrastructure.ai.summarizer import (
    ExtractiveSummaryProvider,
    SummaryService,
    TaggingUnavailableError,
    build_summary_provider,
)
from src.main import app
from src.presentation.api.v1.ai import SearchResultItem


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic provider used without any external AI service."""

    def __init__(
        self,
        *,
        model: str = "fake-model",
        vector: list[float] | None = None,
    ) -> None:
        self._model = model
        self._vector = vector or [1.0, *([0.0] * (VECTOR_DIM - 1))]

    async def embed(self, text: str) -> list[float]:
        return self._vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vector for _ in texts]

    @property
    def provider_name(self) -> EmbeddingProvider:
        return EmbeddingProvider.OPENAI

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return VECTOR_DIM


def test_ai_migration_extends_reference_data_revision() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)

    migration = scripts.get_revision("0003_add_person_embeddings")

    assert migration is not None
    assert migration.down_revision == "0002_seed_person_reference_data"


@pytest.mark.asyncio
async def test_zero_vector_is_rejected_before_persistence() -> None:
    provider = FakeEmbeddingProvider(vector=[0.0] * VECTOR_DIM)
    service = EmbeddingService(provider)

    with pytest.raises(EmbeddingUnavailableError, match="zerowy"):
        await service.embed("test")


@pytest.mark.asyncio
async def test_disabled_provider_reports_embedding_unavailable() -> None:
    provider = build_embedding_provider(provider_name="none")

    assert isinstance(provider, DisabledEmbeddingProvider)
    with pytest.raises(EmbeddingUnavailableError):
        await provider.embed("patron zwierząt")


def test_embedding_cache_key_includes_model_identity() -> None:
    first = EmbeddingService(FakeEmbeddingProvider(model="model-a"))
    second = EmbeddingService(FakeEmbeddingProvider(model="model-b"))

    assert first._cache_key("ten sam tekst") != second._cache_key("ten sam tekst")


def test_none_provider_uses_extractive_summary() -> None:
    provider = build_summary_provider(
        provider_name="none",
        ollama_base_url="http://ollama:11434",
    )

    assert isinstance(provider, ExtractiveSummaryProvider)


@pytest.mark.asyncio
async def test_extractive_provider_does_not_create_empty_ai_tags() -> None:
    provider = ExtractiveSummaryProvider()

    with pytest.raises(TaggingUnavailableError, match="wyłączone"):
        await provider.extract_tags("Biografia", "Testowa postać")


@pytest.mark.asyncio
async def test_semantic_search_uses_asyncpg_compatible_vector_cast() -> None:
    db = AsyncMock()
    query_result = MagicMock()
    query_result.fetchall.return_value = []
    db.execute.return_value = query_result
    service = AIService(
        db,
        embedding_service=EmbeddingService(FakeEmbeddingProvider()),
        summary_service=SummaryService(ExtractiveSummaryProvider()),
    )

    results = await service.semantic_search("patron zwierząt")

    statement = str(db.execute.await_args.args[0])
    assert results == []
    assert "CAST(:query_vector AS vector)" in statement
    assert ":query_vector::vector" not in statement
    assert "p.status = 'published'" in statement


def test_ai_mutation_endpoints_require_bearer_auth() -> None:
    schema = app.openapi()
    paths = (
        "/api/v1/ai/embeddings/{person_id}",
        "/api/v1/ai/summarize/{person_id}",
        "/api/v1/ai/batch/embed",
        "/api/v1/ai/batch/tag",
    )

    for path in paths:
        assert schema["paths"][path]["post"]["security"] == [{"HTTPBearer": []}]


def test_search_result_accepts_negative_cosine_similarity() -> None:
    item = SearchResultItem(
        person_id="person-id",
        canonical_name="Testowa postać",
        slug="testowa-postac",
        person_type="saint",
        similarity_score=-0.25,
    )

    assert item.similarity_score == -0.25
