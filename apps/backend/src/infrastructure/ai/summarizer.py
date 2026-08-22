"""
AI summarization service.

Generates concise, readable summaries of hagiographic biographies.

Supports:
- OpenAI GPT-4o-mini (best quality)
- Ollama Llama3 / Mistral (local, private)
- Extractive fallback (first N sentences – always works)
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from functools import lru_cache

from loguru import logger

# ==============================================================================
# ABSTRACT BASE
# ==============================================================================


class TaggingUnavailableError(RuntimeError):
    """Raised when AI tag suggestions cannot be generated reliably."""


class BaseSummaryProvider(ABC):
    """Abstract summary provider interface."""

    @abstractmethod
    async def summarize(self, text: str, max_words: int = 100) -> str:
        """Generate a summary of the given text."""
        ...

    @abstractmethod
    async def extract_tags(self, text: str, person_name: str) -> list[str]:
        """Extract relevant tags from person biography."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider identifier."""
        ...


# ==============================================================================
# OPENAI PROVIDER
# ==============================================================================


class OpenAISummaryProvider(BaseSummaryProvider):
    """OpenAI GPT-4o-mini for text summarization."""

    MODEL = "gpt-4o-mini"

    def __init__(self, api_key: str, model: str = MODEL) -> None:
        self._model = model
        try:
            from openai import AsyncOpenAI  # type: ignore[import-untyped]

            self._client = AsyncOpenAI(api_key=api_key)
            self._available = True
        except ImportError:
            self._client = None
            self._available = False

    async def summarize(self, text: str, max_words: int = 100) -> str:
        """Summarize biography using GPT-4o-mini."""
        if not self._available or self._client is None:
            return _extractive_summary(text, max_words)

        system_prompt = (
            "Jesteś ekspertem hagiografii katolickiej. "
            "Pisz zwięzłe streszczenia biogramów świętych w języku polskim. "
            "Użyj maksymalnie podanej liczby słów. "
            "Zachowaj najważniejsze fakty: daty, miejsca, patronaty, cuda."
        )
        user_prompt = (
            f"Napisz streszczenie poniższego biogramu w maksymalnie {max_words} słowach:\n\n{text[:4000]}"
        )

        try:
            response = await self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=max_words * 2,
            )
            return response.choices[0].message.content or _extractive_summary(text, max_words)
        except Exception as exc:
            logger.warning(f"OpenAI summarize failed: {exc}")
            return _extractive_summary(text, max_words)

    async def extract_tags(self, text: str, person_name: str) -> list[str]:
        """Extract tags using GPT-4o-mini."""
        if not self._available or self._client is None:
            raise TaggingUnavailableError("Dostawca tagowania OpenAI jest niedostępny")

        prompt = (
            f"Przeanalizuj biogram {person_name} i wylistuj 5-10 tagów tematycznych "
            f"(patronaty, cnoty, zawody, miejsca, stulecia). "
            f'Odpowiedz TYLKO jako obiekt JSON, np. {{"tags": '
            f'["patron zwierząt", "franciszkanin"]}}.\n\n'
            f"Biogram:\n{text[:3000]}"
        )

        try:
            response = await self._client.chat.completions.create(  # type: ignore[union-attr]
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            import json

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            # Handle both {"tags": [...]} and direct array response
            if isinstance(data, list):
                return data[:10]
            if isinstance(data, dict):
                for key in ("tags", "tagi", "keywords", "słowa_kluczowe"):
                    if key in data and isinstance(data[key], list):
                        return data[key][:10]
            raise TaggingUnavailableError("OpenAI nie zwrócił poprawnych propozycji tagów")
        except Exception as exc:
            logger.warning(f"OpenAI tag extraction failed: {exc}")
            if isinstance(exc, TaggingUnavailableError):
                raise
            raise TaggingUnavailableError(
                "Nie udało się wygenerować propozycji tagów OpenAI"
            ) from exc

    @property
    def provider_name(self) -> str:
        return f"openai:{self._model}"


# ==============================================================================
# OLLAMA PROVIDER
# ==============================================================================


class OllamaSummaryProvider(BaseSummaryProvider):
    """Local Ollama LLM for summarization."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def summarize(self, text: str, max_words: int = 100) -> str:
        """Summarize via Ollama."""
        try:
            import httpx

            prompt = (
                f"Napisz streszczenie poniższego biogramu w maksymalnie {max_words} słowach. "
                f"Użyj języka polskiego.\n\n{text[:3000]}"
            )
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json={"model": self._model, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                return response.json().get("response", _extractive_summary(text, max_words))
        except Exception as exc:
            logger.warning(f"Ollama summarize failed: {exc}")
            return _extractive_summary(text, max_words)

    async def extract_tags(self, text: str, person_name: str) -> list[str]:
        """Extract tags via Ollama."""
        try:
            import httpx

            prompt = (
                f"Podaj 5 tagów dla {person_name} oddzielonych przecinkami (patronaty, cnoty, zawody). "
                f"Odpowiedz TYLKO tagami oddzielonymi przecinkami, bez zdań.\n\n{text[:2000]}"
            )
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json={"model": self._model, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                raw = response.json().get("response", "")
                tags = [t.strip() for t in raw.split(",") if t.strip()][:10]
                if not tags:
                    raise TaggingUnavailableError(
                        "Ollama nie zwróciła poprawnych propozycji tagów"
                    )
                return tags
        except Exception as exc:
            logger.warning(f"Ollama tag extraction failed: {exc}")
            if isinstance(exc, TaggingUnavailableError):
                raise
            raise TaggingUnavailableError(
                "Nie udało się wygenerować propozycji tagów Ollama"
            ) from exc

    @property
    def provider_name(self) -> str:
        return f"ollama:{self._model}"


# ==============================================================================
# EXTRACTIVE FALLBACK
# ==============================================================================


class ExtractiveSummaryProvider(BaseSummaryProvider):
    """
    Simple extractive summarizer – no AI required.

    Takes the first N sentences of the text.
    Always works, even without any AI provider.
    """

    async def summarize(self, text: str, max_words: int = 100) -> str:
        return _extractive_summary(text, max_words)

    async def extract_tags(self, text: str, person_name: str) -> list[str]:
        raise TaggingUnavailableError("Automatyczne tagowanie AI jest wyłączone")

    @property
    def provider_name(self) -> str:
        return "extractive-fallback"


# ==============================================================================
# SUMMARY SERVICE
# ==============================================================================


class SummaryService:
    """
    High-level summarization service.

    Orchestrates provider selection and exposes a clean API.
    """

    def __init__(self, provider: BaseSummaryProvider) -> None:
        self._provider = provider

    async def summarize(self, text: str, max_words: int = 100) -> str:
        """
        Generate a concise summary of biographical text.

        Args:
            text: Full biography text in Polish.
            max_words: Maximum number of words in the summary.

        Returns:
            Short summary string.
        """
        if not text or not text.strip():
            return ""
        return await self._provider.summarize(text, max_words)

    async def extract_tags(self, biography: str, person_name: str) -> list[str]:
        """
        Extract relevant tags from a biography.

        Args:
            biography: Full biography text.
            person_name: Name of the person (used as context).

        Returns:
            List of relevant tag strings.
        """
        if not biography or not biography.strip():
            return []
        return await self._provider.extract_tags(biography, person_name)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name


# ==============================================================================
# FACTORY
# ==============================================================================


def build_summary_provider(
    provider_name: str = "none",
    openai_api_key: str | None = None,
    ollama_base_url: str | None = None,
    openai_model: str = OpenAISummaryProvider.MODEL,
    ollama_model: str = "llama3",
) -> BaseSummaryProvider:
    """Build the explicitly configured summary provider."""
    if provider_name == "openai" and openai_api_key:
        logger.info(f"AI: Using OpenAI summary provider ({openai_model})")
        return OpenAISummaryProvider(api_key=openai_api_key, model=openai_model)

    if provider_name == "ollama" and ollama_base_url:
        logger.info(
            f"AI: Using Ollama summary provider ({ollama_base_url}, {ollama_model})"
        )
        return OllamaSummaryProvider(base_url=ollama_base_url, model=ollama_model)

    logger.info("AI: Generative summaries are disabled – using extractive summarizer")
    return ExtractiveSummaryProvider()


@lru_cache(maxsize=1)
def get_summary_service() -> SummaryService:
    """
    Get singleton SummaryService.

    Selects the provider explicitly configured by ``AI_PROVIDER``.
    """
    from src.core.config import settings  # avoid circular import

    provider_name = settings.AI_PROVIDER.value
    openai_key = settings.OPENAI_API_KEY or None
    ollama_url = settings.OLLAMA_BASE_URL or None

    provider = build_summary_provider(
        provider_name=provider_name,
        openai_api_key=openai_key,
        ollama_base_url=ollama_url,
        openai_model=settings.OPENAI_COMPLETION_MODEL,
        ollama_model=settings.OLLAMA_LLM_MODEL,
    )
    return SummaryService(provider)


# ==============================================================================
# UTILITIES
# ==============================================================================


def _extractive_summary(text: str, max_words: int = 100) -> str:
    """
    Simple extractive summary: take first sentences up to max_words words.
    """
    if not text:
        return ""

    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    result_parts: list[str] = []
    word_count = 0

    for sentence in sentences:
        words_in_sentence = len(sentence.split())
        if word_count + words_in_sentence > max_words and result_parts:
            break
        result_parts.append(sentence)
        word_count += words_in_sentence

    summary = " ".join(result_parts)

    # Hard truncate if still too long
    if len(summary.split()) > max_words * 1.5:
        words = summary.split()[:max_words]
        summary = " ".join(words) + "..."

    return summary
