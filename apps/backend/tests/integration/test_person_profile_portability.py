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
from src.application.services.person_profile_service import PersonProfileService
from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonOrder, PublicationStatus
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

    loaded = await PersonService(db_session).get_by_id_or_slug(str(person.id))
    assert loaded is not None
    document = await PersonProfileService(db_session).export_profile(loaded)

    assert document.schema_version == 1
    assert document.profile.status == PublicationStatus.DRAFT
    assert document.profile.latin_name == "Sanctus Exportatus"
    assert document.orders[0].order_slug == order.slug
    assert document.feasts[0].calendar_code == calendar.code
    assert document.sources[0].bibliography is not None
    assert document.sources[0].bibliography.url == "https://example.test/saint"

    document.profile.canonical_name = "Św. Zaimportowany Test"
    document.profile.status = PublicationStatus.PUBLISHED
    validation = await PersonProfileService(db_session).validate_import(document)
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

    duplicate_validation = await PersonProfileService(db_session).validate_import(
        validation.normalized_document
    )
    assert duplicate_validation.can_import is False
    assert "samej nazwie" in duplicate_validation.errors[0]
