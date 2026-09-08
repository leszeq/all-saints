"""Export, validate, and atomically import versioned person profile documents."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.commands.liturgical_calendar import CreateFeastEntryCommand
from src.application.commands.persons import PersonCreateSchema
from src.application.person_profile_models import (
    PersonProfileDocument,
    PersonProfileValidationResult,
    PortableBibliography,
    PortableFeastEntry,
    PortableHistoricalSource,
    PortableOrderMembership,
    PortablePersonData,
    PortablePersonSource,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.calendar_service import CalendarService
from src.application.services.person_service import PersonService
from src.application.services.person_snapshot import (
    append_relation_version,
    serialize_person_snapshot,
)
from src.domain.geography.models import Country, Place, ReligiousOrder
from src.domain.hagiography.models import Person, PersonOrder, PublicationStatus, StateOfLife
from src.domain.identity.models import AuditAction
from src.domain.liturgy.models import Feast, LiturgicalCalendar
from src.domain.sources.models import Bibliography, HistoricalSource, PersonSource


class PersonProfileImportError(ValueError):
    """Raised when a syntactically valid document cannot be safely imported."""

    def __init__(self, validation: PersonProfileValidationResult) -> None:
        self.validation = validation
        super().__init__("Profil nie przeszedł walidacji importu")


class PersonProfileService:
    """Coordinate profile portability without bypassing editorial workflow."""

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

    async def validate_import(
        self, document: PersonProfileDocument
    ) -> PersonProfileValidationResult:
        """Check duplicates and every database reference without mutating data."""
        normalized = document.model_copy(deep=True)
        warnings: list[str] = []
        errors: list[str] = []
        if normalized.profile.status != PublicationStatus.DRAFT:
            warnings.append(
                "Status z pliku zostanie zmieniony na szkic; import nie omija procesu redakcyjnego."
            )
            normalized.profile.status = PublicationStatus.DRAFT

        duplicate = (
            await self.db.execute(
                select(Person.id)
                .where(
                    Person.deleted_at.is_(None),
                    func.lower(Person.canonical_name)
                    == normalized.profile.canonical_name.strip().lower(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            errors.append("Aktywny profil o tej samej nazwie kanonicznej już istnieje.")

        reference_checks = (
            ("birth_country_id", Country, "Kraj urodzenia"),
            ("death_country_id", Country, "Kraj śmierci"),
            ("nationality_id", Country, "Narodowość"),
            ("birth_place_id", Place, "Miejsce urodzenia"),
            ("death_place_id", Place, "Miejsce śmierci"),
            ("state_of_life_id", StateOfLife, "Stan życia"),
        )
        for field, model, label in reference_checks:
            identifier = getattr(normalized.profile, field)
            if identifier is not None:
                reference = await self.db.get(model, identifier)
                if reference is None or getattr(reference, "deleted_at", None) is not None:
                    errors.append(f"{label}: wskazany identyfikator nie istnieje w tej bazie.")

        order_slugs = [membership.order_slug for membership in normalized.orders]
        if len(order_slugs) != len(set(order_slugs)):
            errors.append("Ten sam zakon nie może być przypisany do profilu więcej niż raz.")
        if order_slugs:
            existing_orders = set(
                (
                    await self.db.execute(
                        select(ReligiousOrder.slug).where(
                            ReligiousOrder.slug.in_(order_slugs),
                            ReligiousOrder.deleted_at.is_(None),
                        )
                    )
                ).scalars()
            )
            for missing_slug in sorted(set(order_slugs) - existing_orders):
                errors.append(f"Nie znaleziono wspólnoty o slugu: {missing_slug}.")

        calendar_codes = [entry.calendar_code for entry in normalized.feasts]
        if calendar_codes:
            existing_calendars = set(
                (
                    await self.db.execute(
                        select(LiturgicalCalendar.code).where(
                            LiturgicalCalendar.code.in_(calendar_codes),
                            LiturgicalCalendar.deleted_at.is_(None),
                            LiturgicalCalendar.is_active.is_(True),
                        )
                    )
                ).scalars()
            )
            for missing_code in sorted(set(calendar_codes) - existing_calendars):
                errors.append(f"Nie znaleziono aktywnego kalendarza: {missing_code}.")

        for entry in normalized.feasts:
            try:
                date(2000, entry.month, entry.day)
            except ValueError:
                errors.append(f"Nieprawidłowa data wspomnienia: {entry.month:02d}-{entry.day:02d}.")

        feast_keys = [(entry.calendar_code, entry.month, entry.day) for entry in normalized.feasts]
        if len(feast_keys) != len(set(feast_keys)):
            errors.append("Profil zawiera powtórzone wspomnienie w tym samym kalendarzu i dniu.")

        for entry in normalized.feasts:
            if not entry.is_primary:
                continue
            existing_primary = (
                await self.db.execute(
                    select(Feast.id)
                    .join(Feast.calendar)
                    .where(
                        LiturgicalCalendar.code == entry.calendar_code,
                        Feast.month == entry.month,
                        Feast.day == entry.day,
                        Feast.is_primary.is_(True),
                        Feast.deleted_at.is_(None),
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existing_primary is not None:
                entry.is_primary = False
                warnings.append(
                    f"W dniu {entry.day:02d}.{entry.month:02d} kalendarz "
                    f"{entry.calendar_code} ma już główny wpis; importowane wspomnienie "
                    "zostanie dodane jako dodatkowe."
                )

        return PersonProfileValidationResult(
            can_import=not errors,
            errors=errors,
            warnings=warnings,
            normalized_document=normalized,
        )

    async def import_profile(
        self,
        document: PersonProfileDocument,
        *,
        user_id: uuid.UUID | None,
        audit_context: AuditContext,
    ) -> Person:
        """Persist a validated profile and all supported relations atomically."""
        validation = await self.validate_import(document)
        if not validation.can_import:
            raise PersonProfileImportError(validation)
        normalized = validation.normalized_document
        person = await PersonService(self.db).create_person(
            PersonCreateSchema.model_validate(
                {
                    **normalized.profile.model_dump(mode="json"),
                    "status": PublicationStatus.DRAFT.value,
                }
            ),
            user_id=user_id,
            audit_context=audit_context,
        )
        previous_snapshot = await serialize_person_snapshot(self.db, person)

        if normalized.orders:
            await self._import_orders(person.id, normalized.orders)
        if normalized.feasts:
            await self._import_feasts(person.id, normalized.feasts)
        if normalized.sources:
            await self._import_sources(person.id, normalized.sources)

        if normalized.orders or normalized.sources:
            previous_snapshot, current_snapshot = await append_relation_version(
                self.db,
                person,
                previous_snapshot=previous_snapshot,
                changed_by_id=user_id,
                change_summary="Import relacji profilu z pliku JSON",
            )
            add_audit_log(
                self.db,
                context=audit_context,
                action=AuditAction.UPDATE,
                resource_type="persons",
                resource_id=person.id,
                old_value=previous_snapshot,
                new_value=current_snapshot,
                extra_metadata={"operation": "profile_json_import"},
            )
        await self.db.flush()
        imported = await PersonService(self.db).get_by_id_or_slug(str(person.id))
        assert imported is not None
        return imported

    async def _import_orders(
        self, person_id: uuid.UUID, memberships: list[PortableOrderMembership]
    ) -> None:
        slugs = [membership.order_slug for membership in memberships]
        orders = {
            order.slug: order
            for order in (
                await self.db.execute(
                    select(ReligiousOrder).where(
                        ReligiousOrder.slug.in_(slugs),
                        ReligiousOrder.deleted_at.is_(None),
                    )
                )
            ).scalars()
        }
        for membership in memberships:
            self.db.add(
                PersonOrder(
                    person_id=person_id,
                    order_id=orders[membership.order_slug].id,
                    entry_date=membership.entry_date,
                    exit_date=membership.exit_date,
                    is_founder=membership.is_founder,
                    membership_type=membership.membership_type.value,
                    notes=membership.notes,
                )
            )

    async def _import_feasts(self, person_id: uuid.UUID, entries: list[PortableFeastEntry]) -> None:
        calendar_service = CalendarService(self.db)
        for entry in entries:
            await calendar_service.create_entry(
                CreateFeastEntryCommand.model_validate(
                    {
                        **entry.model_dump(mode="json"),
                        "person_id": person_id,
                    }
                )
            )

    async def _import_sources(
        self, person_id: uuid.UUID, sources: list[PortablePersonSource]
    ) -> None:
        for source in sources:
            if source.kind == "bibliography":
                assert source.bibliography is not None
                bibliography = await self._find_or_create_bibliography(source.bibliography)
                link = PersonSource(
                    person_id=person_id,
                    bibliography_id=bibliography.id,
                    **source.link.model_dump(),
                )
            else:
                assert source.historical_source is not None
                historical_source = await self._find_or_create_historical(source.historical_source)
                link = PersonSource(
                    person_id=person_id,
                    historical_source_id=historical_source.id,
                    **source.link.model_dump(),
                )
            self.db.add(link)
        await self.db.flush()

    async def _find_or_create_bibliography(self, data: PortableBibliography) -> Bibliography:
        identifiers = []
        if data.url:
            identifiers.append(Bibliography.url == data.url)
        if data.doi:
            identifiers.append(Bibliography.doi == data.doi)
        if data.isbn:
            identifiers.append(Bibliography.isbn == data.isbn)
        query = select(Bibliography).where(Bibliography.deleted_at.is_(None))
        if identifiers:
            query = query.where(or_(*identifiers))
        else:
            query = query.where(
                Bibliography.title == data.title,
                Bibliography.authors == data.authors,
                Bibliography.year == data.year,
            )
        existing = (await self.db.execute(query.limit(1))).scalar_one_or_none()
        if existing is not None:
            return existing
        created = Bibliography(**data.model_dump(mode="json"))
        self.db.add(created)
        await self.db.flush()
        return created

    async def _find_or_create_historical(self, data: PortableHistoricalSource) -> HistoricalSource:
        query = select(HistoricalSource).where(HistoricalSource.deleted_at.is_(None))
        if data.repository and data.call_number:
            query = query.where(
                HistoricalSource.repository == data.repository,
                HistoricalSource.call_number == data.call_number,
            )
        else:
            query = query.where(
                HistoricalSource.title == data.title,
                HistoricalSource.date_range == data.date_range,
            )
        existing = (await self.db.execute(query.limit(1))).scalar_one_or_none()
        if existing is not None:
            return existing
        created = HistoricalSource(**data.model_dump(mode="json"))
        self.db.add(created)
        await self.db.flush()
        return created
