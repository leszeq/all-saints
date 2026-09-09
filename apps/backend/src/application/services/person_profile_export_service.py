"""Read-only export of complete person profiles into portable JSON documents."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.person_profile_models import (
    PersonProfileDocument,
    PortableBibliography,
    PortableFeastEntry,
    PortableHistoricalSource,
    PortableOrderMembership,
    PortablePersonData,
    PortablePersonSource,
)
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.liturgy.models import Feast, LiturgicalCalendar
from src.domain.sources.models import PersonSource


class PersonProfileExportService:
    """Build portable profile documents without exposing import operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_profile(self, person: Person) -> PersonProfileDocument:
        """Build a portable document using stable slugs/codes for relations."""
        avatar = next(
            (image for image in person.images if image.deleted_at is None and image.is_primary),
            None,
        )
        profile = PortablePersonData.model_validate(
            {
                "person_type": person.person_type,
                "status": PublicationStatus.DRAFT,
                "canonical_name": person.canonical_name,
                "canonical_name_en": person.canonical_name_en,
                "latin_name": person.latin_name,
                "original_name": person.original_name,
                "surnames": person.surnames,
                "religious_name": person.religious_name,
                "epithets": person.epithets,
                "gender": person.gender,
                "era": person.era,
                "century": person.century,
                "birth_date": person.birth_date,
                "birth_year": person.birth_year,
                "death_date": person.death_date,
                "death_year": person.death_year,
                "birth_place_id": person.birth_place_id,
                "death_place_id": person.death_place_id,
                "birth_country_id": person.birth_country_id,
                "death_country_id": person.death_country_id,
                "nationality_id": person.nationality_id,
                "state_of_life_id": person.state_of_life_id,
                "summary_pl": person.summary_pl,
                "biography_pl": person.biography_pl,
                "summary_en": person.summary_en,
                "biography_en": person.biography_en,
                "iconographic_attributes": person.iconographic_attributes,
                "prayers": person.prayers,
                "works": person.works,
                "liturgical_color": person.liturgical_color,
                "is_featured": person.is_featured,
                "external_ids": person.external_ids,
                "avatar": (
                    {
                        "url": avatar.url,
                        "thumbnail_url": avatar.thumbnail_url,
                        "storage_key": avatar.storage_key,
                        "title": avatar.title,
                        "license": avatar.license,
                        "photographer": avatar.photographer,
                        "source_url": avatar.source_url,
                        "width_px": avatar.width_px,
                        "height_px": avatar.height_px,
                        "file_size_bytes": avatar.file_size_bytes,
                        "mime_type": avatar.mime_type,
                    }
                    if avatar is not None
                    else None
                ),
                "aliases": [
                    {
                        "value": alias.value,
                        "language_code": alias.language_code,
                        "kind": alias.kind,
                    }
                    for alias in person.aliases
                    if alias.deleted_at is None
                ],
                "patronages": [
                    {
                        "patronage_type": patronage.patronage_type,
                        "name_pl": patronage.name_pl,
                        "name_en": patronage.name_en,
                        "description": patronage.description,
                        "is_official": patronage.is_official,
                    }
                    for patronage in person.patronages
                    if patronage.deleted_at is None
                ],
                "beatification": (
                    {
                        "beatification_date": person.beatification.beatification_date,
                        "beatification_year": person.beatification.beatification_year,
                    }
                    if person.beatification is not None
                    else None
                ),
                "canonization": (
                    {
                        "canonization_date": person.canonization.canonization_date,
                        "canonization_year": person.canonization.canonization_year,
                    }
                    if person.canonization is not None
                    else None
                ),
            }
        )
        order_memberships = [
            PortableOrderMembership(
                order_slug=membership.order.slug,
                entry_date=membership.entry_date,
                exit_date=membership.exit_date,
                is_founder=membership.is_founder,
                membership_type=membership.membership_type,
                notes=membership.notes,
            )
            for membership in person.orders
            if membership.order.deleted_at is None
        ]
        feasts = await self._export_feasts(person.id)
        sources = await self._export_sources(person.id)
        return PersonProfileDocument(
            source_person_id=person.id,
            source_slug=person.slug,
            source_status=(
                person.status.value if hasattr(person.status, "value") else str(person.status)
            ),
            profile=profile,
            orders=order_memberships,
            feasts=feasts,
            sources=sources,
        )

    async def _export_feasts(self, person_id: uuid.UUID) -> list[PortableFeastEntry]:
        rows = list(
            (
                await self.db.execute(
                    select(Feast)
                    .join(Feast.calendar)
                    .where(
                        Feast.person_id == person_id,
                        Feast.deleted_at.is_(None),
                        LiturgicalCalendar.deleted_at.is_(None),
                    )
                    .options(joinedload(Feast.calendar))
                    .order_by(LiturgicalCalendar.code.asc(), Feast.month.asc(), Feast.day.asc())
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return [
            PortableFeastEntry(
                calendar_code=entry.calendar.code,
                month=entry.month,
                day=entry.day,
                rank=entry.rank,
                liturgical_color=entry.liturgical_color,
                is_primary=entry.is_primary,
                is_suppressed=entry.is_suppressed,
                notes=entry.notes,
                source_title=entry.source_title,
                source_url=entry.source_url,
            )
            for entry in rows
            if entry.month is not None and entry.day is not None
        ]

    async def _export_sources(self, person_id: uuid.UUID) -> list[PortablePersonSource]:
        links = list(
            (
                await self.db.execute(
                    select(PersonSource)
                    .where(
                        PersonSource.person_id == person_id,
                        PersonSource.deleted_at.is_(None),
                    )
                    .options(
                        joinedload(PersonSource.bibliography),
                        joinedload(PersonSource.historical_source),
                    )
                    .order_by(PersonSource.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        exported: list[PortablePersonSource] = []
        for link in links:
            link_data = {
                "page_reference": link.page_reference,
                "quote": link.quote,
                "relevance_score": link.relevance_score,
                "is_primary": link.is_primary,
                "notes": link.notes,
            }
            if link.bibliography is not None and link.bibliography.deleted_at is None:
                exported.append(
                    PortablePersonSource(
                        kind="bibliography",
                        bibliography=PortableBibliography.model_validate(
                            link.bibliography, from_attributes=True
                        ),
                        link=link_data,
                    )
                )
            elif link.historical_source is not None and link.historical_source.deleted_at is None:
                exported.append(
                    PortablePersonSource(
                        kind="historical",
                        historical_source=PortableHistoricalSource.model_validate(
                            link.historical_source, from_attributes=True
                        ),
                        link=link_data,
                    )
                )
        return exported
