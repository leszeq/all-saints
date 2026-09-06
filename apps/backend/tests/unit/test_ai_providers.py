"""Unit coverage for AI providers, validation, caching, and local fallbacks."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.ai.embeddings import (
    VECTOR_DIM,
    DisabledEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingService,
    EmbeddingUnavailableError,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    _pad_or_truncate,
    _validate_vector,
    build_embedding_provider,
    build_person_embedding_text,
)
from src.infrastructure.ai.summarizer import (
    ExtractiveSummaryProvider,
    OllamaSummaryProvider,
    OpenAISummaryProvider,
    SummaryService,
    TaggingUnavailableError,
    _extractive_summary,
    build_summary_provider,
)


def _vector(first: float = 1.0) -> list[float]:
    return [first, *([0.0] * (VECTOR_DIM - 1))]


class StubEmbeddingProvider:
    provider_name = EmbeddingProvider.OPENAI
    model_name = "stub-model"
    dimensions = VECTOR_DIM

    def __init__(self, vectors: list[list[float]] | None = None) -> None:
        self.vectors = vectors or [_vector()]
        self.embed = AsyncMock(side_effect=lambda _text: self.vectors[0])
        self.embed_batch = AsyncMock(
            side_effect=lambda texts: [self.vectors[index] for index, _ in enumerate(texts)]
        )


class StubRedis:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = values or {}
        self.get = AsyncMock(side_effect=lambda key: self.values.get(key))
        self.setex = AsyncMock(
            side_effect=lambda key, _ttl, value: self.values.__setitem__(key, value)
        )


class StubHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class StubHTTPClient:
    def __init__(self, response: StubHTTPResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests: list[tuple[str, dict[str, object]]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url: str, *, json: dict[str, object]):
        self.requests.append((url, json))
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


@pytest.mark.asyncio
async def test_embedding_service_uses_cache_and_recovers_from_invalid_entries() -> None:
    provider = StubEmbeddingProvider()
    redis = StubRedis()
    service = EmbeddingService(provider, redis)
    key = service._cache_key("pierwszy tekst")
    redis.values[key] = json.dumps(_vector(0.5))

    assert (await service.embed("pierwszy tekst"))[0] == 0.5
    provider.embed.assert_not_awaited()

    redis.values[key] = "not-json"
    assert (await service.embed("pierwszy tekst"))[0] == 1.0
    provider.embed.assert_awaited_once()
    assert json.loads(redis.values[key])[0] == 1.0
    assert service.provider_name == "openai"
    assert service.model_name == "stub-model"
    assert service.vector_dimensions == VECTOR_DIM


@pytest.mark.asyncio
async def test_embedding_batch_combines_cache_and_provider_and_validates_count() -> None:
    provider = StubEmbeddingProvider(vectors=[_vector(0.25), _vector(0.75)])
    redis = StubRedis()
    service = EmbeddingService(provider, redis)
    redis.values[service._cache_key("cached")] = json.dumps(_vector(0.5))

    result = await service.embed_batch(["cached", "new-a", "new-b"])

    assert [vector[0] for vector in result] == [0.5, 0.25, 0.75]
    provider.embed_batch.assert_awaited_once_with(["new-a", "new-b"])

    provider.embed_batch = AsyncMock(return_value=[])
    with pytest.raises(EmbeddingUnavailableError, match="niepełny zestaw"):
        await EmbeddingService(provider).embed_batch(["missing"])


@pytest.mark.asyncio
async def test_embedding_cache_failures_are_non_fatal() -> None:
    provider = StubEmbeddingProvider()
    redis = StubRedis()
    redis.get = AsyncMock(side_effect=RuntimeError("redis unavailable"))
    redis.setex = AsyncMock(side_effect=RuntimeError("redis unavailable"))

    assert (await EmbeddingService(provider, redis).embed("tekst"))[0] == 1.0


def test_embedding_validation_factories_and_document_builder() -> None:
    with pytest.raises(EmbeddingUnavailableError, match="wymiarze"):
        _validate_vector([1.0], VECTOR_DIM)
    with pytest.raises(EmbeddingUnavailableError, match="nieprawidłowe"):
        _validate_vector([float("nan"), *([0.0] * (VECTOR_DIM - 1))], VECTOR_DIM)
    with pytest.raises(EmbeddingUnavailableError, match="zerowy"):
        _validate_vector([0.0] * VECTOR_DIM, VECTOR_DIM)

    assert _pad_or_truncate([1.0], 3) == [1.0, 0.0, 0.0]
    assert _pad_or_truncate([1.0, 2.0, 3.0], 2) == [1.0, 2.0]
    document = build_person_embedding_text(
        "Św. Test",
        biography="Pominięty biogram",
        summary="Streszczenie",
        patronages=["chorzy"],
        tags=["miłosierdzie"],
        categories=["męczennicy"],
        occupations=["lekarz"],
        era="modern",
    )
    assert document == (
        "Św. Test | Epoka: modern | Kategorie: męczennicy | Zawody: lekarz | "
        "Patronaty: chorzy | Tagi: miłosierdzie | Streszczenie"
    )

    assert isinstance(build_embedding_provider(provider_name="openai"), DisabledEmbeddingProvider)
    assert isinstance(build_embedding_provider(provider_name="ollama"), DisabledEmbeddingProvider)
    assert isinstance(
        build_embedding_provider(provider_name="none", vector_dimensions=768),
        DisabledEmbeddingProvider,
    )
    assert isinstance(
        build_embedding_provider(provider_name="ollama", ollama_base_url="http://ollama/"),
        OllamaEmbeddingProvider,
    )


@pytest.mark.asyncio
async def test_openai_embedding_provider_maps_success_and_errors() -> None:
    provider = OpenAIEmbeddingProvider.__new__(OpenAIEmbeddingProvider)
    provider._model = "text-embedding-3-small"
    provider._dimensions = VECTOR_DIM
    provider._available = True
    create = AsyncMock(
        side_effect=[
            SimpleNamespace(data=[SimpleNamespace(embedding=_vector())]),
            SimpleNamespace(
                data=[
                    SimpleNamespace(embedding=_vector(0.25)),
                    SimpleNamespace(embedding=_vector(0.75)),
                ]
            ),
            RuntimeError("provider failure"),
        ]
    )
    provider._client = SimpleNamespace(embeddings=SimpleNamespace(create=create))

    assert (await provider.embed("tekst"))[0] == 1.0
    assert [item[0] for item in await provider.embed_batch(["a", "b"])] == [0.25, 0.75]
    assert provider.provider_name == EmbeddingProvider.OPENAI
    assert provider.model_name == "text-embedding-3-small"
    assert provider.dimensions == VECTOR_DIM
    assert create.await_args_list[0].kwargs["dimensions"] == VECTOR_DIM
    with pytest.raises(EmbeddingUnavailableError, match="OpenAI"):
        await provider.embed("błąd")

    provider._available = False
    with pytest.raises(EmbeddingUnavailableError, match="niedostępny"):
        await provider.embed_batch(["tekst"])


@pytest.mark.asyncio
async def test_ollama_embedding_provider_pads_vectors_and_reports_failures(monkeypatch) -> None:
    import httpx

    success = StubHTTPClient(StubHTTPResponse({"embedding": [1.0, 2.0]}))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: success)
    provider = OllamaEmbeddingProvider(base_url="http://ollama/", model="nomic-test")

    vector = await provider.embed("tekst")
    assert len(vector) == VECTOR_DIM
    assert vector[:2] == [1.0, 2.0]
    assert len(await provider.embed_batch(["a", "b"])) == 2
    assert provider.provider_name == EmbeddingProvider.OLLAMA
    assert provider.model_name == "nomic-test"
    assert provider.dimensions == VECTOR_DIM

    failure = StubHTTPClient(error=RuntimeError("offline"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: failure)
    with pytest.raises(EmbeddingUnavailableError, match="Ollama"):
        await provider.embed("tekst")


@pytest.mark.asyncio
async def test_summary_services_and_extractive_limits() -> None:
    provider = ExtractiveSummaryProvider()
    service = SummaryService(provider)

    assert await service.summarize("   ") == ""
    assert await service.extract_tags("", "Św. Test") == []
    assert service.provider_name == "extractive-fallback"
    assert await service.summarize("Pierwsze zdanie. Drugie zdanie.", max_words=3) == (
        "Pierwsze zdanie."
    )
    assert _extractive_summary("", 10) == ""
    assert _extractive_summary(" ".join(["słowo"] * 20), 5).endswith("...")


@pytest.mark.asyncio
async def test_openai_summary_provider_handles_json_and_fallbacks() -> None:
    provider = OpenAISummaryProvider.__new__(OpenAISummaryProvider)
    provider._model = "gpt-test"
    provider._available = True
    create = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Streszczenie AI"))]
            ),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"tagi": ["a", "b"]}'))]
            ),
            RuntimeError("offline"),
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='{"invalid": true}'))]
            ),
        ]
    )
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    assert await provider.summarize("Długi biogram") == "Streszczenie AI"
    assert await provider.extract_tags("Biogram", "Św. Test") == ["a", "b"]
    assert provider.provider_name == "openai:gpt-test"
    assert await provider.summarize("Zdanie awaryjne.") == "Zdanie awaryjne."
    with pytest.raises(TaggingUnavailableError, match="poprawnych"):
        await provider.extract_tags("Biogram", "Św. Test")

    provider._available = False
    with pytest.raises(TaggingUnavailableError, match="niedostępny"):
        await provider.extract_tags("Biogram", "Św. Test")


@pytest.mark.asyncio
async def test_ollama_summary_provider_maps_response_and_errors(monkeypatch) -> None:
    import httpx

    responses = [
        StubHTTPResponse({"response": "Streszczenie lokalne"}),
        StubHTTPResponse({"response": "tag jeden, tag dwa"}),
    ]

    def client_factory(**_kwargs):
        return StubHTTPClient(responses.pop(0))

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    provider = OllamaSummaryProvider(base_url="http://ollama/", model="llama-test")

    assert await provider.summarize("Biogram") == "Streszczenie lokalne"
    assert await provider.extract_tags("Biogram", "Św. Test") == ["tag jeden", "tag dwa"]
    assert provider.provider_name == "ollama:llama-test"

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **_kwargs: StubHTTPClient(error=RuntimeError("offline")),
    )
    assert await provider.summarize("Zdanie awaryjne.") == "Zdanie awaryjne."
    with pytest.raises(TaggingUnavailableError, match="Ollama"):
        await provider.extract_tags("Biogram", "Św. Test")


def test_summary_provider_factory_selects_explicit_configuration() -> None:
    assert isinstance(build_summary_provider(), ExtractiveSummaryProvider)
    assert isinstance(
        build_summary_provider(provider_name="openai", openai_api_key="test-key"),
        OpenAISummaryProvider,
    )
    assert isinstance(
        build_summary_provider(provider_name="ollama", ollama_base_url="http://ollama"),
        OllamaSummaryProvider,
    )
