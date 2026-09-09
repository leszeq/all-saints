"""Atomically import validated, versioned person profile documents."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select

from src.application.commands.liturgical_calendar import CreateFeastEntryCommand
from src.application.commands.persons import PersonCreateSchema
from src.application.person_profile_models import (
    PersonProfileDocument,
    PersonProfileValidationResult,
    PortableBibliography,
    PortableFeastEntry,
    PortableHistoricalSource,
    PortableOrderMembership,
    PortablePersonSource,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.calendar_service import CalendarService
from src.application.services.person_profile_export_service import (
    PersonProfileExportService,
)
from src.application.services.person_profile_import_validator import (
    PersonProfileImportValidator,
)
from src.application.services.person_query_service import PersonQueryService
from src.application.services.person_service import PersonService
from src.application.services.person_snapshot import (
    append_relation_version,
    serialize_person_snapshot,
)
from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography.models import Person, PersonOrder, PublicationStatus
from src.domain.identity.models import AuditAction
from src.domain.sources.models import Bibliography, HistoricalSource, PersonSource

__all__ = ["PersonProfileImportError", "PersonProfileService"]


class PersonProfileImportError(ValueError):
    """Raised when a syntactically valid document cannot be safely imported."""

    def __init__(self, validation: PersonProfileValidationResult) -> None:
        self.validation = validation
        super().__init__("Profil nie przeszedł walidacji importu")


class PersonProfileService(PersonProfileImportValidator, PersonProfileExportService):
    """Import profiles while retaining compatible validation and export methods."""

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
        imported = await PersonQueryService(self.db).get_by_id_or_slug(str(person.id))
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
