"""PostgreSQL coverage for complete JSON profile round trips."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.liturgical_calendar import CreateFeastEntryCommand
from src.application.commands.persons import PersonCreateSchema
from src.application.commands.religious_orders import (
    AddReligiousOrderMembershipCommand,
    CreateReligiousOrderCommand,
)
from src.application.services.audit_service import AuditContext
from src.application.services.calendar_service import CalendarService
from src.application.services.order_service import OrderService
from src.application.services.person_profile_export_service import (
    PersonProfileExportService,
)
from src.application.services.person_profile_import_validator import (
    PersonProfileImportValidator,
)
from src.application.services.person_profile_service import PersonProfileService
from src.application.services.person_query_service import PersonQueryService
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonOrder, PublicationStatus
from src.domain.identity.models import AuditLog
from src.domain.liturgy.models import CalendarScope, Feast, LiturgicalCalendar
from src.domain.sources.models import Bibliography, PersonSource, SourceType


@pytest.mark.asyncio
async def test_profile_export_validation_and_import_round_trip(
    db_session: AsyncSession,
) -> None:
    calendar = LiturgicalCalendar(
        code="roman_pl",
        name="Kalendarz rzymski dla Polski",
        rite="roman",
        scope=CalendarScope.NATIONAL.value,
        is_active=True,
    )
    db_session.add(calendar)
    order = await OrderService(db_session).create_order(
        CreateReligiousOrderCommand(
            slug="wspolnota-portability-test",
            name="Wspólnota Portability Test",
        )
    )
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Eksportowany Test",
            latin_name="Sanctus Exportatus",
            status=PublicationStatus.DRAFT,
            aliases=[{"value": "Eksportowany", "kind": "alias"}],
            patronages=[
                {
                    "patronage_type": "other",
                    "name_pl": "Patron testów importu",
                }
            ],
        )
    )
    await OrderService(db_session).add_membership(
        order.slug,
        AddReligiousOrderMembershipCommand(
            person_id=person.id,
            membership_type="member",
            entry_date="1901",
        ),
    )
    await CalendarService(db_session).create_entry(
        CreateFeastEntryCommand(
            person_id=person.id,
            calendar_code=calendar.code,
            month=9,
            day=8,
            is_primary=True,
            source_title="Kalendarz testowy",
        )
    )
    bibliography = Bibliography(
        source_type=SourceType.WEBSITE.value,
        title="Źródło profilu testowego",
        url="https://example.test/saint",
        reliability_score=4,
    )
    db_session.add(bibliography)
    await db_session.flush()
    db_session.add(
        PersonSource(
            person_id=person.id,
            bibliography_id=bibliography.id,
            is_primary=True,
            page_reference="sekcja 1",
        )
    )
    await db_session.flush()

    loaded = await PersonQueryService(db_session).get_by_id_or_slug(str(person.id))
    assert loaded is not None
    document = await PersonProfileExportService(db_session).export_profile(loaded)

    assert document.schema_version == 1
    assert document.profile.status == PublicationStatus.DRAFT
    assert document.profile.latin_name == "Sanctus Exportatus"
    assert document.orders[0].order_slug == order.slug
    assert document.feasts[0].calendar_code == calendar.code
    assert document.sources[0].bibliography is not None
    assert document.sources[0].bibliography.url == "https://example.test/saint"

    document.profile.canonical_name = "Św. Zaimportowany Test"
    document.profile.status = PublicationStatus.PUBLISHED
    validation = await PersonProfileImportValidator(db_session).validate_import(document)
    assert validation.can_import is True
    assert validation.normalized_document.profile.status == PublicationStatus.DRAFT
    assert validation.normalized_document.feasts[0].is_primary is False
    assert len(validation.warnings) == 2

    imported = await PersonProfileService(db_session).import_profile(
        validation.normalized_document,
        user_id=None,
        audit_context=AuditContext(),
    )
    assert imported.canonical_name == "Św. Zaimportowany Test"
    assert imported.status == PublicationStatus.DRAFT.value
    assert imported.latin_name == "Sanctus Exportatus"
    assert len(imported.orders) == 1
    assert imported.orders[0].order.slug == order.slug
    assert (
        await db_session.scalar(
            select(func.count()).select_from(Feast).where(Feast.person_id == imported.id)
        )
        == 1
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(PersonSource)
            .where(PersonSource.person_id == imported.id)
        )
        == 1
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(PersonOrder)
            .where(PersonOrder.person_id == imported.id)
        )
        == 1
    )

    duplicate_validation = await PersonProfileImportValidator(db_session).validate_import(
        validation.normalized_document
    )
    assert duplicate_validation.can_import is False
    assert "samej nazwie" in duplicate_validation.errors[0]

    # Replace the original (primary) profile, preserving its identity and history.
    replacement = await PersonProfileExportService(db_session).export_profile(loaded)
    replacement.profile.summary_pl = "Nowe streszczenie z pliku JSON"
    replacement.orders[0].entry_date = "1902"
    replacement.sources[0].link.page_reference = "sekcja 2"
    old_id, old_slug, old_version = loaded.id, loaded.slug, loaded.version
    overwrite_validation = await PersonProfileImportValidator(db_session).validate_import(
        replacement,
        overwrite_person_id=old_id,
        expected_version=old_version,
    )
    assert overwrite_validation.can_import
    assert overwrite_validation.normalized_document.feasts[0].is_primary
    assert not overwrite_validation.warnings
    overwritten = await PersonProfileService(db_session).import_profile(
        replacement,
        overwrite_person_id=old_id,
        expected_version=old_version,
        user_id=None,
        audit_context=AuditContext(),
        granted_permissions={"persons:update"},
    )
    assert (overwritten.id, overwritten.slug) == (old_id, old_slug)
    assert overwritten.version > old_version
    assert overwritten.summary_pl == "Nowe streszczenie z pliku JSON"
    assert len(overwritten.orders) == 1
    assert overwritten.orders[0].entry_date == "1902"
    active_feasts = list(
        (
            await db_session.scalars(
                select(Feast).where(
                    Feast.person_id == old_id,
                    Feast.deleted_at.is_(None),
                )
            )
        ).all()
    )
    assert len(active_feasts) == 1 and active_feasts[0].is_primary
    active_sources = list(
        (
            await db_session.scalars(
                select(PersonSource).where(
                    PersonSource.person_id == old_id,
                    PersonSource.deleted_at.is_(None),
                )
            )
        ).all()
    )
    assert len(active_sources) == 1 and active_sources[0].page_reference == "sekcja 2"
    audit = (
        await db_session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == old_id,
                AuditLog.extra_metadata["operation"].astext == "profile_json_overwrite",
            )
        )
    ).one()
    assert audit.old_value["orders"][0]["entry_date"] == "1901"
    assert audit.new_value["orders"][0]["entry_date"] == "1902"
    assert audit.extra_metadata["previous_document"]["feasts"][0]["is_primary"]

    # An empty list replaces old links, without deleting the shared catalogues.
    replacement.orders = []
    replacement.feasts = []
    replacement.sources = []
    overwritten = await PersonProfileService(db_session).import_profile(
        replacement,
        overwrite_person_id=old_id,
        expected_version=overwritten.version,
        user_id=None,
        audit_context=AuditContext(),
        granted_permissions={"persons:update"},
    )
    assert not overwritten.orders
    assert not (
        await db_session.scalars(
            select(Feast).where(
                Feast.person_id == old_id,
                Feast.deleted_at.is_(None),
            )
        )
    ).all()
    assert not (
        await db_session.scalars(
            select(PersonSource).where(
                PersonSource.person_id == old_id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).all()
    assert await db_session.get(Bibliography, bibliography.id) is not None
