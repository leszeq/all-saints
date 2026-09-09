"""Synchronize editable one-to-one and collection relations of a person."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import (
    PersonAliasInputSchema,
    PersonAvatarInputSchema,
    PersonBeatificationInputSchema,
    PersonCanonizationInputSchema,
    PersonPatronageInputSchema,
)
from src.domain.hagiography.models import (
    Beatification,
    Canonization,
    Patronage,
    Person,
    PersonName,
)
from src.domain.hagiography.person_names import normalize_person_name
from src.domain.sources.models import Image


class PersonRelationSynchronizer:
    """Apply validated relation changes without owning transaction boundaries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_avatar(
        self,
        person: Person,
        avatar: PersonAvatarInputSchema | None,
    ) -> None:
        """Create, update or unset the active primary portrait."""
        result = await self.db.execute(
            select(Image)
            .where(
                Image.person_id == person.id,
                Image.deleted_at.is_(None),
                Image.is_primary.is_(True),
            )
            .order_by(Image.sort_order.asc(), Image.created_at.asc())
        )
        primary_images = list(result.scalars().all())

        if avatar is None:
            for image in primary_images:
                image.is_primary = False
            return

        image = primary_images[0] if primary_images else Image(person_id=person.id)
        for duplicate in primary_images[1:]:
            duplicate.is_primary = False

        previous_url = image.url
        image.url = avatar.url
        image.thumbnail_url = avatar.thumbnail_url
        image.title = avatar.title or f"Portret: {person.canonical_name}"
        image.image_type = "portrait"
        image.license = avatar.license.value
        image.photographer = avatar.photographer
        image.source_url = avatar.source_url
        if avatar.storage_key is not None or avatar.url != previous_url:
            image.storage_key = avatar.storage_key
            image.width_px = avatar.width_px
            image.height_px = avatar.height_px
            image.file_size_bytes = avatar.file_size_bytes
            image.mime_type = avatar.mime_type
        image.is_primary = True
        image.sort_order = 0

        if not primary_images:
            self.db.add(image)

    async def replace_patronages(
        self,
        person: Person,
        patronages: list[PersonPatronageInputSchema],
    ) -> None:
        """Replace the person's structured patronage assignments."""
        await self.db.execute(delete(Patronage).where(Patronage.person_id == person.id))
        for patronage in patronages:
            self.db.add(
                Patronage(
                    person_id=person.id,
                    patronage_type=patronage.patronage_type,
                    name_pl=patronage.name_pl,
                    name_en=patronage.name_en,
                    description=patronage.description,
                    is_official=patronage.is_official,
                )
            )

    async def replace_aliases(
        self,
        person: Person,
        aliases: list[PersonAliasInputSchema],
    ) -> None:
        """Replace searchable alternative names with normalized equivalents."""
        await self.db.execute(delete(PersonName).where(PersonName.person_id == person.id))
        for alias in aliases:
            self.db.add(
                PersonName(
                    person_id=person.id,
                    value=alias.value,
                    normalized_value=normalize_person_name(alias.value),
                    language_code=alias.language_code.lower(),
                    kind=alias.kind.value,
                )
            )

    async def sync_beatification(
        self,
        person: Person,
        data: PersonBeatificationInputSchema | None,
    ) -> None:
        """Create, update or remove the person's beatification record."""
        result = await self.db.execute(
            select(Beatification).where(Beatification.person_id == person.id)
        )
        current = result.scalar_one_or_none()
        if data is None or not (data.beatification_date or data.beatification_year):
            if current is not None:
                await self.db.delete(current)
            return

        if current is None:
            current = Beatification(person_id=person.id)
            self.db.add(current)
            person.beatification = current
        current.beatification_date = data.beatification_date
        current.beatification_year = data.beatification_year

    async def sync_canonization(
        self,
        person: Person,
        data: PersonCanonizationInputSchema | None,
    ) -> None:
        """Create, update or remove the person's canonization record."""
        result = await self.db.execute(
            select(Canonization).where(Canonization.person_id == person.id)
        )
        current = result.scalar_one_or_none()
        if data is None or not (data.canonization_date or data.canonization_year):
            if current is not None:
                await self.db.delete(current)
            return

        if current is None:
            current = Canonization(person_id=person.id)
            self.db.add(current)
            person.canonization = current
        current.canonization_date = data.canonization_date
        current.canonization_year = data.canonization_year
