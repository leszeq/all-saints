"""Source and image verification queries for the editorial quality centre."""

from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.editorial_models import (
    EditorialSourceVerificationItemSchema,
    EditorialSourceVerificationStatsSchema,
)
from src.application.services.editorial_quality import EditorialQualityPolicy
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
    SourceType,
)


class EditorialSourceQualityReader:
    """Read source completeness metrics without owning workflow state."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def stats(self) -> EditorialSourceVerificationStatsSchema:
        source_count, *_ = EditorialQualityPolicy.quality_expressions()
        active_person_filter = and_(
            Person.deleted_at.is_(None),
            Person.status != PublicationStatus.ARCHIVED.value,
        )
        active_persons = (
            await self._db.execute(select(func.count(Person.id)).where(active_person_filter))
        ).scalar_one()
        undocumented_persons = (
            await self._db.execute(
                select(func.count(Person.id)).where(active_person_filter, source_count == 0)
            )
        ).scalar_one()
        bibliography_sources = (
            await self._db.execute(
                select(func.count(Bibliography.id)).where(Bibliography.deleted_at.is_(None))
            )
        ).scalar_one()
        historical_sources = (
            await self._db.execute(
                select(func.count(HistoricalSource.id)).where(HistoricalSource.deleted_at.is_(None))
            )
        ).scalar_one()
        person_source_links = (
            await self._db.execute(
                select(func.count(PersonSource.id)).where(PersonSource.deleted_at.is_(None))
            )
        ).scalar_one()
        images = (
            await self._db.execute(select(func.count(Image.id)).where(Image.deleted_at.is_(None)))
        ).scalar_one()
        unknown_license_images = (
            await self._db.execute(
                select(func.count(Image.id)).where(
                    Image.deleted_at.is_(None),
                    Image.license == ImageLicense.UNKNOWN.value,
                )
            )
        ).scalar_one()

        return EditorialSourceVerificationStatsSchema(
            bibliography_sources=bibliography_sources,
            historical_sources=historical_sources,
            person_source_links=person_source_links,
            documented_persons=active_persons - undocumented_persons,
            undocumented_persons=undocumented_persons,
            images=images,
            unknown_license_images=unknown_license_images,
        )

    async def verification_count(self) -> int:
        missing_bibliography_reliability = (
            await self._db.execute(
                select(func.count(Bibliography.id)).where(
                    Bibliography.deleted_at.is_(None),
                    Bibliography.reliability_score.is_(None),
                )
            )
        ).scalar_one()
        missing_website_url = (
            await self._db.execute(
                select(func.count(Bibliography.id)).where(
                    Bibliography.deleted_at.is_(None),
                    Bibliography.source_type == SourceType.WEBSITE.value,
                    EditorialQualityPolicy.missing_text(Bibliography.url),
                )
            )
        ).scalar_one()
        missing_access_date = (
            await self._db.execute(
                select(func.count(Bibliography.id)).where(
                    Bibliography.deleted_at.is_(None),
                    Bibliography.source_type == SourceType.WEBSITE.value,
                    EditorialQualityPolicy.has_text(Bibliography.url),
                    EditorialQualityPolicy.missing_text(Bibliography.url_access_date),
                )
            )
        ).scalar_one()
        missing_digitization_url = (
            await self._db.execute(
                select(func.count(HistoricalSource.id)).where(
                    HistoricalSource.deleted_at.is_(None),
                    HistoricalSource.is_digitized.is_(True),
                    EditorialQualityPolicy.missing_text(HistoricalSource.digitization_url),
                )
            )
        ).scalar_one()
        unknown_license_images = (
            await self._db.execute(
                select(func.count(Image.id)).where(
                    Image.deleted_at.is_(None),
                    Image.license == ImageLicense.UNKNOWN.value,
                )
            )
        ).scalar_one()
        missing_image_source = (
            await self._db.execute(
                select(func.count(Image.id)).where(
                    Image.deleted_at.is_(None),
                    EditorialQualityPolicy.missing_text(Image.source_url),
                )
            )
        ).scalar_one()
        orphan_source_links = (
            await self._db.execute(
                select(func.count(PersonSource.id)).where(
                    PersonSource.deleted_at.is_(None),
                    PersonSource.bibliography_id.is_(None),
                    PersonSource.historical_source_id.is_(None),
                )
            )
        ).scalar_one()
        return (
            missing_bibliography_reliability
            + missing_website_url
            + missing_access_date
            + missing_digitization_url
            + unknown_license_images
            + missing_image_source
            + orphan_source_links
        )

    async def verification_items(
        self,
        limit: int = 150,
    ) -> tuple[list[EditorialSourceVerificationItemSchema], int]:
        items: list[EditorialSourceVerificationItemSchema] = []

        bibliography_rows = (
            (
                await self._db.execute(
                    select(Bibliography)
                    .where(
                        Bibliography.deleted_at.is_(None),
                        or_(
                            Bibliography.reliability_score.is_(None),
                            and_(
                                Bibliography.source_type == SourceType.WEBSITE.value,
                                EditorialQualityPolicy.missing_text(Bibliography.url),
                            ),
                            and_(
                                Bibliography.source_type == SourceType.WEBSITE.value,
                                EditorialQualityPolicy.has_text(Bibliography.url),
                                EditorialQualityPolicy.missing_text(Bibliography.url_access_date),
                            ),
                        ),
                    )
                    .order_by(Bibliography.updated_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        for bibliography in bibliography_rows:
            if bibliography.reliability_score is None:
                items.append(
                    EditorialSourceVerificationItemSchema(
                        id=bibliography.id,
                        item_type="bibliography",
                        title=bibliography.title,
                        issue_code="missing_reliability_score",
                        issue="Brak oceny wiarygodności źródła",
                        severity="warning",
                        source_url=bibliography.url,
                        updated_at=bibliography.updated_at,
                    )
                )
            if bibliography.source_type == SourceType.WEBSITE.value and not bibliography.url:
                items.append(
                    EditorialSourceVerificationItemSchema(
                        id=bibliography.id,
                        item_type="bibliography",
                        title=bibliography.title,
                        issue_code="missing_website_url",
                        issue="Źródło internetowe nie ma adresu URL",
                        severity="critical",
                        updated_at=bibliography.updated_at,
                    )
                )
            if (
                bibliography.source_type == SourceType.WEBSITE.value
                and bibliography.url
                and not bibliography.url_access_date
            ):
                items.append(
                    EditorialSourceVerificationItemSchema(
                        id=bibliography.id,
                        item_type="bibliography",
                        title=bibliography.title,
                        issue_code="missing_website_access_date",
                        issue="Brak daty dostępu do źródła internetowego",
                        severity="warning",
                        source_url=bibliography.url,
                        updated_at=bibliography.updated_at,
                    )
                )

        historical_rows = (
            (
                await self._db.execute(
                    select(HistoricalSource)
                    .where(
                        HistoricalSource.deleted_at.is_(None),
                        HistoricalSource.is_digitized.is_(True),
                        EditorialQualityPolicy.missing_text(HistoricalSource.digitization_url),
                    )
                    .order_by(HistoricalSource.updated_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        for historical_source in historical_rows:
            items.append(
                EditorialSourceVerificationItemSchema(
                    id=historical_source.id,
                    item_type="historical_source",
                    title=historical_source.title,
                    issue_code="missing_digitization_url",
                    issue="Źródło oznaczone jako zdigitalizowane bez linku",
                    severity="warning",
                    updated_at=historical_source.updated_at,
                )
            )

        image_rows = (
            (
                await self._db.execute(
                    select(Image)
                    .where(
                        Image.deleted_at.is_(None),
                        or_(
                            Image.license == ImageLicense.UNKNOWN.value,
                            EditorialQualityPolicy.missing_text(Image.source_url),
                        ),
                    )
                    .options(selectinload(Image.person))
                    .order_by(Image.updated_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        for image in image_rows:
            related_person = image.person
            if image.license == ImageLicense.UNKNOWN.value:
                items.append(
                    EditorialSourceVerificationItemSchema(
                        id=image.id,
                        item_type="image",
                        title=image.title or image.url,
                        issue_code="unknown_image_license",
                        issue="Nieznana licencja obrazu",
                        severity="critical",
                        related_person_id=related_person.id if related_person else None,
                        related_person_name=(
                            related_person.canonical_name if related_person else None
                        ),
                        source_url=image.source_url,
                        updated_at=image.updated_at,
                    )
                )
            if not image.source_url:
                items.append(
                    EditorialSourceVerificationItemSchema(
                        id=image.id,
                        item_type="image",
                        title=image.title or image.url,
                        issue_code="missing_image_source_url",
                        issue="Brak adresu źródła obrazu",
                        severity="warning",
                        related_person_id=related_person.id if related_person else None,
                        related_person_name=(
                            related_person.canonical_name if related_person else None
                        ),
                        updated_at=image.updated_at,
                    )
                )

        orphan_rows = (
            await self._db.execute(
                select(PersonSource, Person)
                .join(Person, Person.id == PersonSource.person_id)
                .where(
                    PersonSource.deleted_at.is_(None),
                    PersonSource.bibliography_id.is_(None),
                    PersonSource.historical_source_id.is_(None),
                    Person.deleted_at.is_(None),
                )
                .order_by(PersonSource.updated_at.desc())
                .limit(limit)
            )
        ).all()
        for link, person in orphan_rows:
            items.append(
                EditorialSourceVerificationItemSchema(
                    id=link.id,
                    item_type="person_source",
                    title=f"Przypis źródłowy: {person.canonical_name}",
                    issue_code="orphan_person_source",
                    issue="Przypis nie wskazuje na bibliografię ani źródło historyczne",
                    severity="critical",
                    related_person_id=person.id,
                    related_person_name=person.canonical_name,
                    updated_at=link.updated_at,
                )
            )

        items.sort(
            key=lambda item: (
                0 if item.severity == "critical" else 1,
                item.updated_at,
            )
        )
        return items[:limit], await self.verification_count()
