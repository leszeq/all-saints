"""
Application Service for Person (Saints, Blessed, etc.) management.
Handles CRUD, slug generation, version snapshotting, FTS, and soft-delete/restore.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from slugify import slugify
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.hagiography.models import (
    Era,
    EraPeriod,
    Gender,
    Patronage,
    PatronageGroup,
    Person,
    PersonType,
    PersonVersion,
    PublicationStatus,
)
from src.domain.identity.models import User
from src.domain.sources.models import Image
from src.presentation.api.v1.persons.schemas import (
    PersonAvatarInputSchema,
    PersonCreateSchema,
    PersonPatronageInputSchema,
    PersonUpdateSchema,
)

ERA_PERIOD_ERAS: dict[EraPeriod, tuple[Era, ...]] = {
    EraPeriod.EARLY_WITNESSES: (
        Era.APOSTOLIC,
        Era.EARLY_CHURCH,
        Era.LATE_ANTIQUITY,
    ),
    EraPeriod.MEDIEVAL: (Era.MEDIEVAL,),
    EraPeriod.RENEWAL: (Era.EARLY_MODERN,),
    EraPeriod.MODERN: (Era.MODERN, Era.CONTEMPORARY),
}

PATRONAGE_GROUP_TYPES: dict[PatronageGroup, tuple[str, ...]] = {
    PatronageGroup.HEALTH: ("illness", "healthcare"),
    PatronageGroup.FAMILY: ("family",),
    PatronageGroup.WORK: ("profession", "work"),
    PatronageGroup.TRAVEL: ("travel",),
}


class PersonService:
    """Service handling Person domain operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _sync_avatar(
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

    async def _replace_patronages(
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

    async def _generate_unique_slug(self, name: str, person_id: uuid.UUID | None = None) -> str:
        """Generate a URL-safe unique slug for a person."""
        base_slug = slugify(name) or "person"
        slug = base_slug
        counter = 1

        while True:
            stmt = select(Person).where(Person.slug == slug)
            if person_id:
                stmt = stmt.where(Person.id != person_id)
            res = await self.db.execute(stmt)
            if res.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    async def create_person(self, data: PersonCreateSchema, user_id: uuid.UUID | None = None) -> Person:
        """Create a new person record."""
        slug = await self._generate_unique_slug(data.canonical_name)

        person = Person(
            slug=slug,
            person_type=data.person_type.value,
            status=data.status.value,
            canonical_name=data.canonical_name,
            canonical_name_en=data.canonical_name_en,
            latin_name=data.latin_name,
            original_name=data.original_name,
            surnames=data.surnames,
            religious_name=data.religious_name,
            epithets=data.epithets,
            gender=data.gender.value,
            era=data.era.value if data.era else None,
            century=data.century,
            birth_date=data.birth_date,
            birth_year=data.birth_year,
            death_date=data.death_date,
            death_year=data.death_year,
            birth_place_id=data.birth_place_id,
            death_place_id=data.death_place_id,
            birth_country_id=data.birth_country_id,
            death_country_id=data.death_country_id,
            nationality_id=data.nationality_id,
            state_of_life_id=data.state_of_life_id,
            summary_pl=data.summary_pl,
            biography_pl=data.biography_pl,
            summary_en=data.summary_en,
            biography_en=data.biography_en,
            iconographic_attributes=data.iconographic_attributes,
            prayers=data.prayers,
            works=data.works,
            liturgical_color=data.liturgical_color.value if data.liturgical_color else None,
            is_featured=data.is_featured,
            external_ids=data.external_ids,
            version=1,
        )

        self.db.add(person)
        await self.db.flush()

        if data.avatar is not None:
            await self._sync_avatar(person, data.avatar)
        if data.patronages:
            await self._replace_patronages(person, data.patronages)

        # Create initial version snapshot
        version_snapshot = PersonVersion(
            person_id=person.id,
            version_number=1,
            snapshot=jsonable_encoder(person.to_dict()),
            changed_by_id=user_id,
            changed_at=datetime.now(UTC).isoformat(),
            change_summary="Utworzenie rekordu",
        )
        self.db.add(version_snapshot)

        await self.db.commit()
        await self.db.refresh(person)
        await self.db.refresh(person, attribute_names=["images", "state_of_life", "patronages"])
        return person

    async def get_by_id_or_slug(self, identifier: str) -> Person | None:
        """Fetch person by UUID or slug."""
        stmt = (
            select(Person)
            .options(
                selectinload(Person.images),
                selectinload(Person.state_of_life),
                selectinload(Person.patronages),
            )
            .where(Person.deleted_at.is_(None))
        )
        try:
            val_uuid = uuid.UUID(identifier)
            stmt = stmt.where(Person.id == val_uuid)
        except ValueError:
            stmt = stmt.where(Person.slug == identifier)

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_persons(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        person_type: PersonType | None = None,
        status: PublicationStatus | None = None,
        gender: Gender | None = None,
        era: Era | None = None,
        period: EraPeriod | None = None,
        patronage: PatronageGroup | None = None,
        country_id: uuid.UUID | None = None,
        is_featured: bool | None = None,
    ) -> tuple[list[Person], int]:
        """List persons with full-text search, filtering, and pagination."""
        query = (
            select(Person)
            .options(selectinload(Person.images))
            .where(Person.deleted_at.is_(None))
        )

        # Filters
        if person_type:
            query = query.where(Person.person_type == person_type.value)
        if status:
            query = query.where(Person.status == status.value)
        if gender:
            query = query.where(Person.gender == gender.value)
        if period:
            query = query.where(
                Person.era.in_([era.value for era in ERA_PERIOD_ERAS[period]])
            )
        elif era:
            query = query.where(Person.era == era.value)
        if patronage:
            query = query.where(
                Person.patronages.any(
                    and_(
                        Patronage.deleted_at.is_(None),
                        Patronage.patronage_type.in_(PATRONAGE_GROUP_TYPES[patronage]),
                    )
                )
            )
        if country_id:
            query = query.where(
                or_(Person.birth_country_id == country_id, Person.death_country_id == country_id)
            )
        if is_featured is not None:
            query = query.where(Person.is_featured == is_featured)

        # Search (Full-text search fallback to LIKE for multi-word queries)
        if search and search.strip():
            term = search.strip()
            query = query.where(
                or_(
                    Person.canonical_name.ilike(f"%{term}%"),
                    Person.latin_name.ilike(f"%{term}%"),
                    Person.summary_pl.ilike(f"%{term}%"),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        # Paginate
        query = query.order_by(Person.canonical_name.asc()).offset((page - 1) * per_page).limit(per_page)
        res = await self.db.execute(query)
        persons = list(res.scalars().all())

        return persons, total

    async def get_last_editors(
        self,
        person_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, User]:
        """Return the user responsible for the latest version of each person."""
        if not person_ids:
            return {}

        ranked_versions = (
            select(
                PersonVersion.person_id.label("person_id"),
                PersonVersion.changed_by_id.label("changed_by_id"),
                func.row_number()
                .over(
                    partition_by=PersonVersion.person_id,
                    order_by=PersonVersion.version_number.desc(),
                )
                .label("position"),
            )
            .where(PersonVersion.person_id.in_(person_ids))
            .subquery()
        )
        result = await self.db.execute(
            select(ranked_versions.c.person_id, User)
            .join(User, User.id == ranked_versions.c.changed_by_id)
            .where(ranked_versions.c.position == 1)
        )
        return dict(result.all())

    async def update_person(
        self,
        person: Person,
        data: PersonUpdateSchema,
        user_id: uuid.UUID | None = None,
    ) -> Person:
        """Update person record and create version snapshot."""
        avatar_was_set = "avatar" in data.model_fields_set
        patronages_were_set = "patronages" in data.model_fields_set
        update_dict = data.model_dump(
            exclude_unset=True,
            exclude={"avatar", "patronages", "change_summary"},
        )

        if "canonical_name" in update_dict and update_dict["canonical_name"] != person.canonical_name:
            person.slug = await self._generate_unique_slug(update_dict["canonical_name"], person.id)

        for key, value in update_dict.items():
            if hasattr(person, key):
                setattr(person, key, value.value if hasattr(value, "value") else value)

        if avatar_was_set:
            await self._sync_avatar(person, data.avatar)
        if patronages_were_set:
            await self._replace_patronages(person, data.patronages or [])

        person.version += 1
        person.updated_at = datetime.now(UTC)

        # Save new version snapshot
        version_snapshot = PersonVersion(
            person_id=person.id,
            version_number=person.version,
            snapshot=jsonable_encoder(person.to_dict()),
            changed_by_id=user_id,
            changed_at=datetime.now(UTC).isoformat(),
            change_summary=data.change_summary or "Aktualizacja danych",
        )
        self.db.add(version_snapshot)

        await self.db.commit()
        await self.db.refresh(person)
        await self.db.refresh(person, attribute_names=["images", "state_of_life", "patronages"])
        return person

    async def soft_delete_person(self, person: Person, user_id: uuid.UUID | None = None) -> None:
        """Soft delete a person record."""
        person.deleted_at = datetime.now(UTC)
        await self.db.commit()

    async def restore_person(
        self,
        person_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Person | None:
        """Restore a soft-deleted person record."""
        stmt = (
            select(Person)
            .options(
                selectinload(Person.images),
                selectinload(Person.state_of_life),
                selectinload(Person.patronages),
            )
            .where(Person.id == person_id)
        )
        res = await self.db.execute(stmt)
        person = res.scalar_one_or_none()
        if person and person.deleted_at is not None:
            person.deleted_at = None
            person.version += 1
            person.updated_at = datetime.now(UTC)
            self.db.add(
                PersonVersion(
                    person_id=person.id,
                    version_number=person.version,
                    snapshot=jsonable_encoder(person.to_dict()),
                    changed_by_id=user_id,
                    changed_at=datetime.now(UTC).isoformat(),
                    change_summary="Przywrócenie rekordu",
                )
            )
            await self.db.commit()
            await self.db.refresh(person)
            await self.db.refresh(person, attribute_names=["images", "state_of_life", "patronages"])
        return person

    async def get_person_versions(self, person_id: uuid.UUID) -> list[PersonVersion]:
        """Fetch version history for a person."""
        stmt = (
            select(PersonVersion)
            .where(PersonVersion.person_id == person_id)
            .order_by(PersonVersion.version_number.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
