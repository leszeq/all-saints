"""PostgreSQL integration coverage for the liturgical calendar service."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.commands.liturgical_calendar import (
    CreateFeastEntryCommand,
    CreateLiturgicalObservanceCommand,
    UpdateFeastEntryCommand,
    UpdateLiturgicalObservanceCommand,
)
from src.application.services.calendar_service import (
    CalendarNotFoundError,
    CalendarService,
    FeastConflictError,
    FeastNotFoundError,
    ObservanceConflictError,
    ObservanceNotFoundError,
)
from src.domain.hagiography.models import Gender, Person, PersonType, PublicationStatus
from src.domain.liturgy.models import (
    CalendarScope,
    Feast,
    FeastRank,
    LiturgicalCalendar,
    LiturgicalObservance,
    ObservanceType,
)


async def _seed_catalogue(
    db_session: AsyncSession,
) -> tuple[dict[str, LiturgicalCalendar], Person, Person]:
    calendars = {
        code: LiturgicalCalendar(
            id=uuid.uuid4(),
            code=code,
            name=name,
            rite="roman",
            scope=scope,
            is_active=True,
        )
        for code, name, scope in (
            ("roman_universal", "Kalendarz powszechny", CalendarScope.UNIVERSAL.value),
            ("roman_pl", "Kalendarz polski", CalendarScope.NATIONAL.value),
            ("roman_martyrology", "Martyrologium", CalendarScope.UNIVERSAL.value),
        )
    }
    published = Person(
        id=uuid.uuid4(),
        slug="sw-test-kalendarza",
        canonical_name="Św. Test Kalendarza",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.UNKNOWN.value,
        is_featured=True,
    )
    draft = Person(
        id=uuid.uuid4(),
        slug="szkic-kalendarza",
        canonical_name="Szkic Kalendarza",
        person_type=PersonType.CANDIDATE.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
    )
    db_session.add_all([*calendars.values(), published, draft])
    await db_session.commit()
    return calendars, published, draft


@pytest.mark.asyncio
async def test_calendar_service_defers_commit_to_unit_of_work(
    db_session: AsyncSession,
    test_engine,
) -> None:
    await _seed_catalogue(db_session)
    observance = await CalendarService(db_session).create_observance(
        CreateLiturgicalObservanceCommand(
            slug="transakcja-obchodu-test",
            title_pl="Transakcja obchodu testowego",
            observance_type=ObservanceType.OTHER,
        )
    )
    observer_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with observer_factory() as observer:
        before_commit = await observer.scalar(
            select(LiturgicalObservance).where(LiturgicalObservance.id == observance.id)
        )
        assert before_commit is None

        await db_session.commit()

        after_commit = await observer.scalar(
            select(LiturgicalObservance).where(LiturgicalObservance.id == observance.id)
        )
        assert after_commit is not None


@pytest.mark.asyncio
async def test_observance_crud_and_conflict_rules(db_session: AsyncSession) -> None:
    calendars, _, _ = await _seed_catalogue(db_session)
    service = CalendarService(db_session)

    assert {calendar.code for calendar in await service.list_calendars()} == set(calendars)
    assert (await service.get_calendar("roman_pl")).id == calendars["roman_pl"].id
    with pytest.raises(CalendarNotFoundError):
        await service.get_calendar("missing")

    created = await service.create_observance(
        CreateLiturgicalObservanceCommand(
            slug="matki-bozej-testowej",
            title_pl="Matki Bożej Testowej",
            observance_type=ObservanceType.MARIAN,
            is_featured=True,
        )
    )
    assert (await service.get_observance(created.id)).slug == "matki-bozej-testowej"
    assert (await service.get_observance(created.slug)).id == created.id
    assert [item.id for item in await service.list_observances()] == [created.id]

    with pytest.raises(ObservanceConflictError):
        await service.create_observance(
            CreateLiturgicalObservanceCommand(
                slug=created.slug,
                title_pl="Duplikat obchodu",
                observance_type=ObservanceType.OTHER,
            )
        )

    updated = await service.update_observance(
        created.id,
        UpdateLiturgicalObservanceCommand(
            slug="matki-bozej-zmienionej",
            title_pl="Matki Bożej Zmienionej",
            is_featured=False,
        ),
    )
    assert updated.slug == "matki-bozej-zmienionej"
    assert updated.is_featured is False

    await service.delete_observance(updated.id)
    assert await service.list_observances() == []
    with pytest.raises(ObservanceNotFoundError):
        await service.get_observance(updated.id)


@pytest.mark.asyncio
async def test_calendar_entries_merge_public_targets_and_maintain_primary(
    db_session: AsyncSession,
) -> None:
    calendars, published, draft = await _seed_catalogue(db_session)
    service = CalendarService(db_session)
    observance = await service.create_observance(
        CreateLiturgicalObservanceCommand(
            slug="uroczystosc-testowa",
            title_pl="Uroczystość Testowa",
            observance_type=ObservanceType.LORD,
            is_featured=True,
        )
    )

    universal = await service.create_entry(
        CreateFeastEntryCommand(
            person_id=published.id,
            calendar_code="roman_universal",
            month=8,
            day=29,
            rank=FeastRank.MEMORIAL,
            source_title="Źródło testowe",
            source_url="https://example.com/calendar",
        )
    )
    draft_entry = await service.create_entry(
        CreateFeastEntryCommand(
            person_id=draft.id,
            calendar_code="roman_pl",
            month=8,
            day=29,
        )
    )
    observance_entry = await service.create_entry(
        CreateFeastEntryCommand(
            observance_id=observance.id,
            calendar_code="roman_pl",
            month=8,
            day=29,
            rank=FeastRank.SOLEMNITY,
            is_primary=True,
        )
    )

    selected, entries = await service.get_day(
        date(2026, 8, 29),
        include_martyrology=False,
    )
    assert selected.code == "roman_pl"
    assert [entry.id for entry in entries] == [observance_entry.id, universal.id]
    assert draft_entry.id not in {entry.id for entry in entries}

    _, grouped = await service.get_month(
        year=2026,
        month=8,
        include_martyrology=False,
    )
    assert [entry.id for entry in grouped[29]] == [observance_entry.id, universal.id]
    assert [entry.id for entry in await service.list_person_entries(published.id)] == [universal.id]

    with pytest.raises(FeastConflictError):
        await service.create_entry(
            CreateFeastEntryCommand(
                person_id=published.id,
                calendar_code="roman_universal",
                month=8,
                day=29,
            )
        )

    changed = await service.update_entry(
        universal.id,
        UpdateFeastEntryCommand(
            calendar_code="roman_pl",
            month=8,
            day=30,
            rank=FeastRank.FEAST,
            is_primary=True,
            notes="Przeniesione",
        ),
    )
    assert changed.calendar_id == calendars["roman_pl"].id
    assert (changed.month, changed.day, changed.day_of_year) == (8, 30, 243)
    assert changed.rank == FeastRank.FEAST.value
    assert changed.is_primary is True

    await service.delete_entry(changed.id)
    with pytest.raises(FeastNotFoundError):
        await service.get_entry(changed.id)


@pytest.mark.asyncio
async def test_calendar_service_rejects_missing_targets_and_invalid_updates(
    db_session: AsyncSession,
) -> None:
    _, published, _ = await _seed_catalogue(db_session)
    service = CalendarService(db_session)

    with pytest.raises(FeastNotFoundError, match="Osoba"):
        await service.create_entry(
            CreateFeastEntryCommand(
                person_id=uuid.uuid4(),
                calendar_code="roman_pl",
                month=1,
                day=1,
            )
        )
    with pytest.raises(FeastNotFoundError, match="Obchód"):
        await service.create_entry(
            CreateFeastEntryCommand(
                observance_id=uuid.uuid4(),
                calendar_code="roman_pl",
                month=1,
                day=1,
            )
        )
    with pytest.raises(FeastNotFoundError, match="Osoba"):
        await service.list_person_entries(uuid.uuid4())

    entry = await service.create_entry(
        CreateFeastEntryCommand(
            person_id=published.id,
            calendar_code="roman_pl",
            month=1,
            day=2,
        )
    )
    with pytest.raises(ValueError, match="miesiąca i dnia"):
        await service.update_entry(entry.id, UpdateFeastEntryCommand(month=None))
    with pytest.raises(ValueError):
        await service.get_month(year=2026, month=13)


@pytest.mark.asyncio
async def test_public_calendar_excludes_unresolved_moveable_placeholders(
    db_session: AsyncSession,
) -> None:
    calendars, published, _ = await _seed_catalogue(db_session)
    db_session.add(
        Feast(
            person_id=published.id,
            calendar_id=calendars["roman_pl"].id,
            month=8,
            day=30,
            day_of_year=243,
            date_note="Przykładowa nierozstrzygnięta reguła ruchoma",
            is_moveable=True,
            rank=FeastRank.MEMORIAL.value,
            is_primary=False,
            is_suppressed=False,
        )
    )
    await db_session.flush()

    _, entries = await CalendarService(db_session).get_day(
        date(2026, 8, 30),
        include_universal=False,
        include_martyrology=False,
    )

    assert entries == []
