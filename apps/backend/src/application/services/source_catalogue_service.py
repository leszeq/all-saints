"""Application service for source catalogues and public source statistics."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.source_catalogue import (
    CreateBibliographyCommand,
    CreateHistoricalSourceCommand,
)
from src.application.source_models import SourceStatsResult
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
)

T = TypeVar("T")


class SourceCatalogueService:
    """Read and create source records inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_public_stats(self) -> SourceStatsResult:
        """Return source counts constrained to the public person catalogue."""
        published_person_filter = (
            Person.deleted_at.is_(None),
            Person.status == PublicationStatus.PUBLISHED.value,
        )
        active_person_source_filter = (
            PersonSource.deleted_at.is_(None),
            or_(
                and_(
                    PersonSource.bibliography_id.is_not(None),
                    PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
                ),
                and_(
                    PersonSource.historical_source_id.is_not(None),
                    PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
                ),
            ),
        )

        total_published_persons = await self.db.scalar(
            select(func.count(Person.id)).where(*published_person_filter)
        )
        documented_persons = await self.db.scalar(
            select(func.count(func.distinct(PersonSource.person_id)))
            .join(Person, Person.id == PersonSource.person_id)
            .where(*published_person_filter, *active_person_source_filter)
        )
        person_source_links = await self.db.scalar(
            select(func.count(PersonSource.id))
            .join(Person, Person.id == PersonSource.person_id)
            .where(*published_person_filter, *active_person_source_filter)
        )
        bibliography_sources = await self.db.scalar(
            select(func.count(Bibliography.id)).where(Bibliography.deleted_at.is_(None))
        )
        historical_sources = await self.db.scalar(
            select(func.count(HistoricalSource.id)).where(HistoricalSource.deleted_at.is_(None))
        )
        images = await self.db.scalar(
            select(func.count(Image.id))
            .join(Person, Person.id == Image.person_id)
            .where(*published_person_filter, Image.deleted_at.is_(None))
        )
        unknown_license_images = await self.db.scalar(
            select(func.count(Image.id))
            .join(Person, Person.id == Image.person_id)
            .where(
                *published_person_filter,
                Image.deleted_at.is_(None),
                Image.license == ImageLicense.UNKNOWN.value,
            )
        )

        return SourceStatsResult(
            bibliography_sources=int(bibliography_sources or 0),
            historical_sources=int(historical_sources or 0),
            person_source_links=int(person_source_links or 0),
            documented_persons=int(documented_persons or 0),
            total_published_persons=int(total_published_persons or 0),
            images=int(images or 0),
            unknown_license_images=int(unknown_license_images or 0),
        )

    async def list_bibliography(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Bibliography], int]:
        """Return one filtered page of active bibliography records."""
        query = select(Bibliography).where(Bibliography.deleted_at.is_(None))
        if search:
            query = query.where(
                Bibliography.title.ilike(f"%{search}%") | Bibliography.authors.ilike(f"%{search}%")
            )
        query = query.order_by(Bibliography.year.desc().nullslast(), Bibliography.title.asc())
        return await self._execute_page(query, page=page, per_page=per_page)

    async def create_bibliography(
        self,
        data: CreateBibliographyCommand,
    ) -> Bibliography:
        """Create a bibliography record."""
        bibliography = Bibliography(**data.model_dump(mode="json"))
        self.db.add(bibliography)
        await self.db.flush()
        await self.db.refresh(bibliography)
        return bibliography

    async def list_historical_sources(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[HistoricalSource], int]:
        """Return one filtered page of active historical sources."""
        query = select(HistoricalSource).where(HistoricalSource.deleted_at.is_(None))
        if search:
            query = query.where(
                HistoricalSource.title.ilike(f"%{search}%")
                | HistoricalSource.repository.ilike(f"%{search}%")
            )
        query = query.order_by(HistoricalSource.title.asc())
        return await self._execute_page(query, page=page, per_page=per_page)

    async def create_historical_source(
        self,
        data: CreateHistoricalSourceCommand,
    ) -> HistoricalSource:
        """Create a primary historical-source record."""
        historical_source = HistoricalSource(**data.model_dump(mode="json"))
        self.db.add(historical_source)
        await self.db.flush()
        await self.db.refresh(historical_source)
        return historical_source

    async def _execute_page(
        self,
        statement: Select[tuple[T]],
        *,
        page: int,
        per_page: int,
    ) -> tuple[list[T], int]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await self.db.execute(count_statement)).scalar_one())
        result = await self.db.execute(statement.offset((page - 1) * per_page).limit(per_page))
        return list(result.scalars().all()), total
