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
    Beatification,
    Canonization,
    Era,
    EraPeriod,
    Gender,
    Patronage,
    PatronageGroup,
    Person,
    PersonOrder,
    PersonSort,
    PersonType,
    PersonVersion,
    PublicationStatus,
)
from src.domain.identity.models import User
from src.domain.sources.models import Image
from src.presentation.api.v1.persons.schemas import (
    PersonAvatarInputSchema,
    PersonBeatificationInputSchema,
    PersonCanonizationInputSchema,
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


class PersonStatusChangeError(ValueError):
    """Raised when CRUD attempts to bypass the editorial workflow."""


class PersonVersionConflictError(RuntimeError):
    """Raised when an editor submits a stale person representation."""

    def __init__(self, expected_version: int, current_version: int) -> None:
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"Rekord ma już wersję {current_version}, a formularz wersję "
            f"{expected_version}. Odśwież stronę i ponów zmiany."
        )


def _enum_values(value: object | list[object] | tuple[object, ...] | set[object] | None) -> list[str]:
    """Normalize a single enum/query value or a multi-select value list."""
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        raw_values = value
    else:
        raw_values = (value,)
    return [
        item.value if hasattr(item, "value") else str(item)
        for item in raw_values
        if item is not None
    ]


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

    @staticmethod
    def _beatification_has_content(data: PersonBeatificationInputSchema) -> bool:
        return bool(data.beatification_date or data.beatification_year)

    @staticmethod
    def _canonization_has_content(data: PersonCanonizationInputSchema) -> bool:
        return bool(data.canonization_date or data.canonization_year)

    async def _sync_beatification(
        self,
        person: Person,
        data: PersonBeatificationInputSchema | None,
    ) -> None:
        """Create, update or remove the person's beatification record."""
        current = person.beatification
        if data is None or not self._beatification_has_content(data):
            if current is not None:
                await self.db.delete(current)
            return

        if current is None:
            current = Beatification(person_id=person.id)
            self.db.add(current)
            person.beatification = current
        current.beatification_date = data.beatification_date
        current.beatification_year = data.beatification_year

    async def _sync_canonization(
        self,
        person: Person,
        data: PersonCanonizationInputSchema | None,
    ) -> None:
        """Create, update or remove the person's canonization record."""
        current = person.canonization
        if data is None or not self._canonization_has_content(data):
            if current is not None:
                await self.db.delete(current)
            return

        if current is None:
            current = Canonization(person_id=person.id)
            self.db.add(current)
            person.canonization = current
        current.canonization_date = data.canonization_date
        current.canonization_year = data.canonization_year

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
        if data.status != PublicationStatus.DRAFT:
            raise PersonStatusChangeError(
                "Nowy rekord musi rozpocząć proces redakcyjny jako szkic"
            )
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
        if data.beatification and self._beatification_has_content(data.beatification):
            self.db.add(
                Beatification(
                    person_id=person.id,
                    beatification_date=data.beatification.beatification_date,
                    beatification_year=data.beatification.beatification_year,
                )
            )
        if data.canonization and self._canonization_has_content(data.canonization):
            self.db.add(
                Canonization(
                    person_id=person.id,
                    canonization_date=data.canonization.canonization_date,
                    canonization_year=data.canonization.canonization_year,
                )
            )

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
        await self.db.refresh(
            person,
            attribute_names=[
                "images",
                "state_of_life",
                "patronages",
                "orders",
                "beatification",
                "canonization",
            ],
        )
        return person

    async def get_by_id_or_slug(
        self,
        identifier: str,
        *,
        published_only: bool = False,
    ) -> Person | None:
        """Fetch a person by UUID or slug, optionally limiting access to public records."""
        stmt = (
            select(Person)
            .options(
                selectinload(Person.images),
                selectinload(Person.state_of_life),
                selectinload(Person.patronages),
                selectinload(Person.orders).selectinload(PersonOrder.order),
                selectinload(Person.beatification),
                selectinload(Person.canonization),
            )
            .where(Person.deleted_at.is_(None))
        )
        if published_only:
            stmt = stmt.where(Person.status == PublicationStatus.PUBLISHED.value)
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
        person_type: PersonType | list[PersonType] | None = None,
        status: PublicationStatus | None = None,
        gender: Gender | list[Gender] | None = None,
        era: Era | list[Era] | None = None,
        period: EraPeriod | list[EraPeriod] | None = None,
        patronage: PatronageGroup | list[PatronageGroup] | None = None,
        country_id: uuid.UUID | None = None,
        is_featured: bool | None = None,
        published_only: bool = False,
        sort: PersonSort = PersonSort.NAME_ASC,
    ) -> tuple[list[Person], int]:
        """List persons with full-text search, filtering, and pagination."""
        query = (
            select(Person)
            .options(selectinload(Person.images), selectinload(Person.patronages))
            .where(Person.deleted_at.is_(None))
        )

        if published_only:
            query = query.where(Person.status == PublicationStatus.PUBLISHED.value)

        # Filters
        person_type_values = _enum_values(person_type)
        if person_type_values:
            query = query.where(Person.person_type.in_(person_type_values))
        if status and not published_only:
            query = query.where(Person.status == status.value)
        gender_values = _enum_values(gender)
        if gender_values:
            query = query.where(Person.gender.in_(gender_values))
        period_values = _enum_values(period)
        era_values = _enum_values(era)
        if period_values:
            period_eras: set[str] = set()
            for period_value in period_values:
                period_eras.update(
                    era.value for era in ERA_PERIOD_ERAS[EraPeriod(period_value)]
                )
            query = query.where(Person.era.in_(sorted(period_eras)))
        elif era_values:
            query = query.where(Person.era.in_(era_values))
        patronage_values = _enum_values(patronage)
        if patronage_values:
            patronage_types: set[str] = set()
            for patronage_value in patronage_values:
                patronage_types.update(PATRONAGE_GROUP_TYPES[PatronageGroup(patronage_value)])
            query = query.where(
                Person.patronages.any(
                    and_(
                        Patronage.deleted_at.is_(None),
                        Patronage.patronage_type.in_(sorted(patronage_types)),
                    )
                )
            )
        if country_id:
            query = query.where(
                or_(Person.birth_country_id == country_id, Person.death_country_id == country_id)
            )
        if is_featured is not None:
            query = query.where(Person.is_featured == is_featured)

        search_score = None
        if search and search.strip():
            term = search.strip()
            like_term = f"%{term}%"
            text_query = func.websearch_to_tsquery("simple", func.unaccent(term))
            full_text_rank = func.coalesce(
                func.ts_rank_cd(Person.search_vector, text_query),
                0.0,
            )
            fuzzy_rank = func.greatest(
                func.similarity(Person.canonical_name, term),
                func.similarity(func.coalesce(Person.canonical_name_en, ""), term),
                func.similarity(func.coalesce(Person.latin_name, ""), term),
            )
            search_score = full_text_rank + (fuzzy_rank * 0.25)
            query = query.where(
                or_(
                    Person.search_vector.op("@@")(text_query),
                    Person.canonical_name.ilike(like_term),
                    Person.canonical_name_en.ilike(like_term),
                    Person.latin_name.ilike(like_term),
                    Person.canonical_name.op("%")(term),
                    Person.canonical_name_en.op("%")(term),
                    Person.latin_name.op("%")(term),
                    Person.patronages.any(
                        and_(
                            Patronage.deleted_at.is_(None),
                            or_(
                                Patronage.name_pl.ilike(like_term),
                                Patronage.name_en.ilike(like_term),
                                Patronage.description.ilike(like_term),
                                Patronage.patronage_type.ilike(like_term),
                            ),
                        )
                    ),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar_one()

        # Paginate
        if search_score is not None:
            query = query.order_by(search_score.desc(), Person.canonical_name.asc())
        elif sort == PersonSort.UPDATED_DESC:
            query = query.order_by(Person.updated_at.desc(), Person.canonical_name.asc())
        else:
            query = query.order_by(Person.canonical_name.asc())
        query = query.offset((page - 1) * per_page).limit(per_page)
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
        *,
        allow_status_change: bool = False,
    ) -> Person:
        """Update person record and create version snapshot."""
        status_was_set = "status" in data.model_fields_set
        if status_was_set:
            requested_status = data.status.value if data.status is not None else None
            current_status = (
                person.status.value if hasattr(person.status, "value") else str(person.status)
            )
            if requested_status is None:
                raise PersonStatusChangeError("Status rekordu nie może być pusty")
            if requested_status != current_status and not allow_status_change:
                raise PersonStatusChangeError(
                    "Status rekordu można zmienić wyłącznie przez workflow redakcyjny"
                )

        # Serialize modifications of the same row and refresh the version after
        # waiting for another transaction. This closes the check/write race;
        # expected_version additionally detects an editor submitting a stale form.
        loaded_version = person.version
        await self.db.refresh(
            person,
            attribute_names=["version"],
            with_for_update=True,
        )
        expected_version = (
            data.expected_version if data.expected_version is not None else loaded_version
        )
        if expected_version != person.version:
            raise PersonVersionConflictError(expected_version, person.version)

        avatar_was_set = "avatar" in data.model_fields_set
        patronages_were_set = "patronages" in data.model_fields_set
        beatification_was_set = "beatification" in data.model_fields_set
        canonization_was_set = "canonization" in data.model_fields_set
        update_dict = data.model_dump(
            exclude_unset=True,
            exclude={
                "avatar",
                "patronages",
                "beatification",
                "canonization",
                "change_summary",
                "expected_version",
            },
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
        if beatification_was_set:
            await self._sync_beatification(person, data.beatification)
        if canonization_was_set:
            await self._sync_canonization(person, data.canonization)

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
        await self.db.refresh(
            person,
            attribute_names=[
                "images",
                "state_of_life",
                "patronages",
                "orders",
                "beatification",
                "canonization",
            ],
        )
        for membership in person.orders:
            await self.db.refresh(membership, attribute_names=["order"])
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
                selectinload(Person.orders).selectinload(PersonOrder.order),
                selectinload(Person.beatification),
                selectinload(Person.canonization),
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
            await self.db.refresh(
                person,
                attribute_names=[
                    "images",
                    "state_of_life",
                    "patronages",
                    "orders",
                    "beatification",
                    "canonization",
                ],
            )
            for membership in person.orders:
                await self.db.refresh(membership, attribute_names=["order"])
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
