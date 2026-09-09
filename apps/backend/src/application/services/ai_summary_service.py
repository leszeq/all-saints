"""AI-assisted summary and tag generation use cases."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import Person
from src.infrastructure.ai.summarizer import SummaryService, get_summary_service


class AISummaryService:
    """Generate non-destructive AI drafts for one person profile."""

    def __init__(
        self,
        db: AsyncSession,
        summary_service: SummaryService | None = None,
    ) -> None:
        self._db = db
        self._summaries = summary_service or get_summary_service()

    @property
    def summary_provider(self) -> str:
        """Return the configured summary and tagging provider identifier."""
        return self._summaries.provider_name

    async def generate_summary(
        self,
        person_id: uuid.UUID,
        max_words: int = 100,
    ) -> str | None:
        """Generate and persist a working summary for one active person."""
        person = await self._get_person(person_id)
        if person is None:
            return None

        biography = person.biography_pl or person.summary_pl or ""
        if not biography.strip():
            return ""

        summary = await self._summaries.summarize(biography, max_words=max_words)
        person.ai_summary = summary
        await self._db.flush()
        return summary

    async def extract_person_tags(self, person_id: uuid.UUID) -> list[str]:
        """Generate and persist tag suggestions for one active person."""
        person = await self._get_person(person_id)
        if person is None:
            return []

        tags = await self._summaries.extract_tags(
            person.biography_pl or "",
            person.canonical_name,
        )
        person.ai_tags = tags
        await self._db.flush()
        return tags

    async def _get_person(self, person_id: uuid.UUID) -> Person | None:
        result = await self._db.execute(
            select(Person).where(Person.id == person_id, Person.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
