"""
Application service for person mutations.

Read operations remain inherited temporarily for backwards compatibility while
new callers depend directly on ``PersonQueryService``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from slugify import slugify
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from src.application.commands.persons import (
    PersonAliasInputSchema,
    PersonAvatarInputSchema,
    PersonBeatificationInputSchema,
    PersonCanonizationInputSchema,
    PersonCreateSchema,
    PersonPatronageInputSchema,
    PersonUpdateSchema,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_query_service import (
    ERA_PERIOD_ERAS,
    PATRONAGE_GROUP_TYPES,
    PersonQueryService,
)
from src.application.services.person_snapshot import serialize_person_snapshot
from src.domain.hagiography.models import (
    Beatification,
    Canonization,
    Patronage,
    Person,
    PersonName,
    PersonOrder,
    PersonVersion,
    PublicationStatus,
)
from src.domain.hagiography.person_names import normalize_person_name
from src.domain.identity.models import AuditAction
from src.domain.sources.models import Image

__all__ = [
    "ERA_PERIOD_ERAS",
    "PATRONAGE_GROUP_TYPES",
    "PersonService",
    "PersonStatusChangeError",
    "PersonVersionConflictError",
]


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


class PersonService(PersonQueryService):
    """Mutate people while retaining the legacy read-compatible interface."""

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

    async def _replace_aliases(
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
        """Generate a URL-safe slug unique across active and soft-deleted people.

        Soft-deleted rows deliberately remain in this lookup. Their public URL is
        reserved so that restoring a record cannot collide with a newer person or
        silently point an established canonical URL at different content.
        """
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

    async def create_person(
        self,
        data: PersonCreateSchema,
        user_id: uuid.UUID | None = None,
        *,
        audit_context: AuditContext | None = None,
    ) -> Person:
        """Create a new person record."""
        if data.status != PublicationStatus.DRAFT:
            raise PersonStatusChangeError("Nowy rekord musi rozpocząć proces redakcyjny jako szkic")
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
        if data.aliases:
            await self._replace_aliases(person, data.aliases)
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
        person_snapshot = await serialize_person_snapshot(self.db, person)
        version_snapshot = PersonVersion(
            person_id=person.id,
            version_number=1,
            snapshot=person_snapshot,
            changed_by_id=user_id,
            changed_at=datetime.now(UTC),
            change_summary="Utworzenie rekordu",
        )
        self.db.add(version_snapshot)
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(user_id),
            action=AuditAction.CREATE,
            resource_type="persons",
            resource_id=person.id,
            new_value=person_snapshot,
        )

        await self.db.flush()
        await self.db.refresh(person)
        await self.db.refresh(
            person,
            attribute_names=[
                "images",
                "aliases",
                "state_of_life",
                "patronages",
                "orders",
                "beatification",
                "canonization",
            ],
        )
        return person

    async def update_person(
        self,
        person: Person,
        data: PersonUpdateSchema,
        user_id: uuid.UUID | None = None,
        *,
        allow_status_change: bool = False,
        audit_context: AuditContext | None = None,
    ) -> Person:
        """Update person record and create version snapshot."""
        previous_status = (
            person.status.value if hasattr(person.status, "value") else str(person.status)
        )
        status_was_set = "status" in data.model_fields_set
        if status_was_set:
            requested_status = data.status.value if data.status is not None else None
            if requested_status is None:
                raise PersonStatusChangeError("Status rekordu nie może być pusty")
            if requested_status != previous_status and not allow_status_change:
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
        previous_snapshot = await serialize_person_snapshot(self.db, person)

        avatar_was_set = "avatar" in data.model_fields_set
        aliases_were_set = "aliases" in data.model_fields_set
        patronages_were_set = "patronages" in data.model_fields_set
        beatification_was_set = "beatification" in data.model_fields_set
        canonization_was_set = "canonization" in data.model_fields_set
        update_dict = data.model_dump(
            exclude_unset=True,
            exclude={
                "avatar",
                "aliases",
                "patronages",
                "beatification",
                "canonization",
                "change_summary",
                "expected_version",
            },
        )

        if (
            "canonical_name" in update_dict
            and update_dict["canonical_name"] != person.canonical_name
        ):
            person.slug = await self._generate_unique_slug(update_dict["canonical_name"], person.id)

        for key, value in update_dict.items():
            if hasattr(person, key):
                setattr(person, key, value.value if hasattr(value, "value") else value)

        if avatar_was_set:
            await self._sync_avatar(person, data.avatar)
        if aliases_were_set:
            await self._replace_aliases(person, data.aliases or [])
        if patronages_were_set:
            await self._replace_patronages(person, data.patronages or [])
        if beatification_was_set:
            await self._sync_beatification(person, data.beatification)
        if canonization_was_set:
            await self._sync_canonization(person, data.canonization)

        person.version += 1
        person.updated_at = datetime.now(UTC)

        # Save new version snapshot
        person_snapshot = await serialize_person_snapshot(self.db, person)
        version_snapshot = PersonVersion(
            person_id=person.id,
            version_number=person.version,
            snapshot=person_snapshot,
            changed_by_id=user_id,
            changed_at=datetime.now(UTC),
            change_summary=data.change_summary or "Aktualizacja danych",
        )
        self.db.add(version_snapshot)
        current_status = (
            person.status.value if hasattr(person.status, "value") else str(person.status)
        )
        action = AuditAction.UPDATE
        if (
            previous_status != current_status
            and current_status == PublicationStatus.PUBLISHED.value
        ):
            action = AuditAction.PUBLISH
        elif (
            previous_status == PublicationStatus.PUBLISHED.value
            and current_status != previous_status
        ):
            action = AuditAction.UNPUBLISH
        audit_metadata: dict[str, object] = {
            "change_summary": data.change_summary or "Aktualizacja danych",
        }
        if previous_status != current_status:
            audit_metadata.update(
                previous_status=previous_status,
                status=current_status,
            )
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(user_id),
            action=action,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=person_snapshot,
            extra_metadata=audit_metadata,
        )

        await self.db.flush()
        await self.db.refresh(person)
        await self.db.refresh(
            person,
            attribute_names=[
                "images",
                "aliases",
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

    async def soft_delete_person(
        self,
        person: Person,
        user_id: uuid.UUID | None = None,
        *,
        audit_context: AuditContext | None = None,
    ) -> None:
        """Soft delete a person record."""
        previous_snapshot = await serialize_person_snapshot(self.db, person)
        person.deleted_at = datetime.now(UTC)
        person.version += 1
        person.updated_at = datetime.now(UTC)
        current_snapshot = await serialize_person_snapshot(self.db, person)
        self.db.add(
            PersonVersion(
                person_id=person.id,
                version_number=person.version,
                snapshot=current_snapshot,
                changed_by_id=user_id,
                changed_at=datetime.now(UTC),
                change_summary="Usunięcie rekordu",
            )
        )
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(user_id),
            action=AuditAction.DELETE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
        )
        await self.db.flush()

    async def restore_person(
        self,
        person_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        *,
        audit_context: AuditContext | None = None,
    ) -> Person | None:
        """Restore a soft-deleted person record."""
        stmt = (
            select(Person)
            .options(
                selectinload(Person.images),
                selectinload(Person.aliases),
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
            previous_snapshot = await serialize_person_snapshot(self.db, person)
            person.deleted_at = None
            person.version += 1
            person.updated_at = datetime.now(UTC)
            current_snapshot = await serialize_person_snapshot(self.db, person)
            self.db.add(
                PersonVersion(
                    person_id=person.id,
                    version_number=person.version,
                    snapshot=current_snapshot,
                    changed_by_id=user_id,
                    changed_at=datetime.now(UTC),
                    change_summary="Przywrócenie rekordu",
                )
            )
            add_audit_log(
                self.db,
                context=audit_context or AuditContext.for_user(user_id),
                action=AuditAction.RESTORE,
                resource_type="persons",
                resource_id=person.id,
                old_value=previous_snapshot,
                new_value=current_snapshot,
            )
            await self.db.flush()
            await self.db.refresh(person)
            await self.db.refresh(
                person,
                attribute_names=[
                    "images",
                    "aliases",
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
        return None
