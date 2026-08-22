"""
Embedding service for vector similarity search.

Supports explicitly configured providers:
1. OpenAI text-embedding-3-small (1536 dim) – best quality
2. Ollama nomic-embed-text (768 dim → padded to 1536)
3. Disabled provider – reports that semantic search is unavailable

Usage:
    service = get_embedding_service()
    vector = await service.embed("Święty Franciszek z Asyżu, patron zwierząt")
"""

from __future__ import annotations

import hashlib
import json
import math
from abc import ABC, abstractmethod
from enum import StrEnum
from functools import lru_cache

from loguru import logger

VECTOR_DIM = 1536  # Standard dimension (OpenAI text-embedding-3-small)


# ==============================================================================
# PROVIDER ENUM
# ==============================================================================


class EmbeddingProvider(StrEnum):
    """Available embedding providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    DISABLED = "disabled"


class EmbeddingUnavailableError(RuntimeError):
    """Raised when a real, usable embedding cannot be generated."""


# ==============================================================================
# ABSTRACT BASE
# ==============================================================================


class BaseEmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> EmbeddingProvider:
        """Return provider identifier."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model name."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        ...


# ==============================================================================
# OPENAI PROVIDER
# ==============================================================================


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI text-embedding-3-small provider (1536 dimensions)."""

    MODEL = "text-embedding-3-small"
    DIM = 1536

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str = MODEL,
        dimensions: int = DIM,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]

            self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            self._available = True
        except ImportError:
            logger.warning("openai package not installed – OpenAI provider disabled")
            self._client = None
            self._available = False

    async def embed(self, text: str) -> list[float]:
        """Embed a single text via OpenAI API."""
        if not self._available or self._client is None:
            raise EmbeddingUnavailableError("Dostawca embeddingów OpenAI jest niedostępny")
        try:
            request: dict[str, object] = {
                "input": text[:8192],
                "model": self._model,
            }
            if self._model.startswith("text-embedding-3"):
                request["dimensions"] = self._dimensions
            response = await self._client.embeddings.create(**request)
            return response.data[0].embedding
        except Exception as exc:
            logger.warning(f"OpenAI embed failed: {exc}")
            raise EmbeddingUnavailableError("Nie udało się wygenerować embeddingu OpenAI") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call."""
        if not self._available or self._client is None:
            raise EmbeddingUnavailableError("Dostawca embeddingów OpenAI jest niedostępny")
        try:
            request: dict[str, object] = {
                "input": [text[:8192] for text in texts],
                "model": self._model,
            }
            if self._model.startswith("text-embedding-3"):
                request["dimensions"] = self._dimensions
            response = await self._client.embeddings.create(**request)
            return [item.embedding for item in response.data]
        except Exception as exc:
            logger.warning(f"OpenAI batch embed failed: {exc}")
            raise EmbeddingUnavailableError("Nie udało się wygenerować embeddingów OpenAI") from exc

    @property
    def provider_name(self) -> EmbeddingProvider:
        return EmbeddingProvider.OPENAI

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions


# ==============================================================================
# OLLAMA PROVIDER
# ==============================================================================


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama nomic-embed-text provider (768 dim, padded to 1536)."""

    MODEL = "nomic-embed-text"
    NATIVE_DIM = 768

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = MODEL,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._available = True

    async def embed(self, text: str) -> list[float]:
        """Embed via local Ollama instance."""
        try:
            import httpx  # type: ignore[import-untyped]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text[:4096]},
                )
                response.raise_for_status()
                vec = response.json()["embedding"]
                return _pad_or_truncate(vec, VECTOR_DIM)
        except Exception as exc:
            logger.warning(f"Ollama embed failed: {exc}")
            self._available = False
            raise EmbeddingUnavailableError("Nie udało się wygenerować embeddingu Ollama") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts sequentially via Ollama."""
        results = []
        for text in texts:
            vec = await self.embed(text)
            results.append(vec)
        return results

    @property
    def provider_name(self) -> EmbeddingProvider:
        return EmbeddingProvider.OLLAMA

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return VECTOR_DIM


# ==============================================================================
# DISABLED PROVIDER
# ==============================================================================


class DisabledEmbeddingProvider(BaseEmbeddingProvider):
    """Provider used when semantic embeddings are intentionally disabled."""

    def __init__(self, reason: str = "Moduł embeddingów jest wyłączony") -> None:
        self._reason = reason

    async def embed(self, text: str) -> list[float]:
        raise EmbeddingUnavailableError(self._reason)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingUnavailableError(self._reason)

    @property
    def provider_name(self) -> EmbeddingProvider:
        return EmbeddingProvider.DISABLED

    @property
    def model_name(self) -> str:
        return "disabled"

    @property
    def dimensions(self) -> int:
        return VECTOR_DIM


# ==============================================================================
# EMBEDDING SERVICE (orchestrator with Redis cache)
# ==============================================================================


class EmbeddingService:
    """
    High-level embedding service with Redis caching.

    Uses the provider selected in application settings. Invalid, missing and
    zero-valued vectors are rejected before they can enter cache or storage.
    """

    CACHE_TTL = 60 * 60 * 24 * 7  # 7 days

    def __init__(self, provider: BaseEmbeddingProvider, redis_client: object | None = None) -> None:
        self._provider = provider
        self._redis = redis_client

    # ── Public API ─────────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        """
        Embed text with Redis caching.

        Args:
            text: Input text to embed.

        Returns:
            Float vector of VECTOR_DIM dimensions.
        """
        cache_key = self._cache_key(text)

        # Try cache first
        if self._redis is not None:
            try:
                cached = await self._redis.get(cache_key)  # type: ignore[union-attr]
                if cached:
                    cached_vector = json.loads(cached)
                    _validate_vector(cached_vector, self.vector_dimensions)
                    return cached_vector
            except Exception as exc:
                logger.debug(f"Ignoring invalid embedding cache entry: {exc}")

        vector = await self._provider.embed(text)
        _validate_vector(vector, self.vector_dimensions)

        # Store in cache
        if self._redis is not None:
            try:
                await self._redis.setex(cache_key, self.CACHE_TTL, json.dumps(vector))  # type: ignore[union-attr]
            except Exception as exc:
                logger.debug(f"Could not cache embedding: {exc}")

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts, using cache where available."""
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Check cache for each text
        for i, text in enumerate(texts):
            if self._redis is not None:
                try:
                    cached = await self._redis.get(self._cache_key(text))  # type: ignore[union-attr]
                    if cached:
                        cached_vector = json.loads(cached)
                        _validate_vector(cached_vector, self.vector_dimensions)
                        results[i] = cached_vector
                        continue
                except Exception as exc:
                    logger.debug(f"Ignoring invalid embedding cache entry: {exc}")
            uncached_indices.append(i)
            uncached_texts.append(text)

        # Embed uncached texts
        if uncached_texts:
            vectors = await self._provider.embed_batch(uncached_texts)
            if len(vectors) != len(uncached_texts):
                raise EmbeddingUnavailableError(
                    "Dostawca zwrócił niepełny zestaw embeddingów"
                )
            for idx, vec in zip(uncached_indices, vectors, strict=True):
                _validate_vector(vec, self.vector_dimensions)
                results[idx] = vec
                if self._redis is not None:
                    try:
                        await self._redis.setex(  # type: ignore[union-attr]
                            self._cache_key(texts[idx]),
                            self.CACHE_TTL,
                            json.dumps(vec),
                        )
                    except Exception as exc:
                        logger.debug(f"Could not cache embedding: {exc}")

        if any(result is None for result in results):
            raise EmbeddingUnavailableError("Nie udało się wygenerować wszystkich embeddingów")
        return [result for result in results if result is not None]

    @property
    def provider_name(self) -> str:
        """Return the active provider name."""
        return self._provider.provider_name.value

    @property
    def model_name(self) -> str:
        """Return the active model name."""
        return self._provider.model_name

    @property
    def vector_dimensions(self) -> int:
        """Return vector dimensionality."""
        return self._provider.dimensions

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode()).hexdigest()[:24]
        return (
            f"emb:{self.provider_name}:{self.model_name}:"
            f"{self.vector_dimensions}:{digest}"
        )


# ==============================================================================
# FACTORY
# ==============================================================================


def build_embedding_provider(
    provider_name: str = "none",
    openai_api_key: str | None = None,
    openai_base_url: str | None = None,
    ollama_base_url: str | None = None,
    openai_model: str = OpenAIEmbeddingProvider.MODEL,
    ollama_model: str = OllamaEmbeddingProvider.MODEL,
    vector_dimensions: int = VECTOR_DIM,
) -> BaseEmbeddingProvider:
    """
    Build the explicitly configured embedding provider.
    """
    if vector_dimensions != VECTOR_DIM:
        return DisabledEmbeddingProvider(
            f"Baza danych obsługuje embeddingi o wymiarze {VECTOR_DIM}, "
            f"a skonfigurowano {vector_dimensions}"
        )

    if provider_name == EmbeddingProvider.OPENAI.value:
        if not openai_api_key:
            return DisabledEmbeddingProvider("Brak klucza API dla dostawcy OpenAI")
        logger.info(f"AI: Using OpenAI embedding provider ({openai_model})")
        return OpenAIEmbeddingProvider(
            api_key=openai_api_key,
            base_url=openai_base_url,
            model=openai_model,
            dimensions=vector_dimensions,
        )

    if provider_name == EmbeddingProvider.OLLAMA.value:
        if not ollama_base_url:
            return DisabledEmbeddingProvider("Brak adresu usługi Ollama")
        logger.info(f"AI: Using Ollama embedding provider ({ollama_base_url})")
        return OllamaEmbeddingProvider(base_url=ollama_base_url, model=ollama_model)

    logger.info("AI: Semantic embeddings are disabled")
    return DisabledEmbeddingProvider()


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    Get singleton EmbeddingService instance.

    Reads configuration from settings and optionally wires Redis cache.
    """
    from src.core.config import settings  # avoid circular import

    openai_key = settings.OPENAI_API_KEY or None
    ollama_url = settings.OLLAMA_BASE_URL or None

    provider = build_embedding_provider(
        provider_name=settings.AI_PROVIDER.value,
        openai_api_key=openai_key,
        ollama_base_url=ollama_url,
        openai_model=settings.OPENAI_EMBEDDING_MODEL,
        ollama_model=settings.OLLAMA_EMBEDDING_MODEL,
        vector_dimensions=settings.EMBEDDING_DIMENSIONS,
    )

    # Try to get Redis client for caching
    redis_client = None
    try:
        from src.infrastructure.cache.redis_client import get_redis_client  # type: ignore[import]

        redis_client = get_redis_client()
    except Exception:
        logger.debug("Redis not available – embedding cache disabled")

    return EmbeddingService(provider=provider, redis_client=redis_client)


# ==============================================================================
# UTILITIES
# ==============================================================================


def _validate_vector(vector: list[float], expected_dimensions: int) -> None:
    """Reject malformed and zero vectors before caching or persistence."""
    if len(vector) != expected_dimensions:
        raise EmbeddingUnavailableError(
            f"Dostawca zwrócił embedding o wymiarze {len(vector)} zamiast {expected_dimensions}"
        )
    if not all(math.isfinite(float(value)) for value in vector):
        raise EmbeddingUnavailableError("Embedding zawiera nieprawidłowe wartości")
    if not any(float(value) != 0.0 for value in vector):
        raise EmbeddingUnavailableError("Dostawca zwrócił pusty embedding zerowy")


def _pad_or_truncate(vec: list[float], target_dim: int) -> list[float]:
    """Pad a vector with zeros or truncate it to target dimension."""
    if len(vec) >= target_dim:
        return vec[:target_dim]
    return vec + [0.0] * (target_dim - len(vec))


def build_person_embedding_text(
    canonical_name: str,
    biography: str | None = None,
    summary: str | None = None,
    patronages: list[str] | None = None,
    tags: list[str] | None = None,
    categories: list[str] | None = None,
    occupations: list[str] | None = None,
    era: str | None = None,
) -> str:
    """
    Build the text document used for generating person embeddings.

    Combines all relevant semantic fields into a single string
    that captures the essence of the person for vector search.
    """
    parts: list[str] = []

    # Core identity
    parts.append(canonical_name)

    if era:
        parts.append(f"Epoka: {era}")

    if categories:
        parts.append("Kategorie: " + ", ".join(categories))

    if occupations:
        parts.append("Zawody: " + ", ".join(occupations))

    if patronages:
        parts.append("Patronaty: " + ", ".join(patronages))

    if tags:
        parts.append("Tagi: " + ", ".join(tags))

    # Summary takes precedence over full biography for conciseness
    if summary:
        parts.append(summary[:1000])
    elif biography:
        parts.append(biography[:1000])

    return " | ".join(parts)
