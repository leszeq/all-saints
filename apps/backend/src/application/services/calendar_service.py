"""Application service for liturgical calendars and daily commemorations."""

from __future__ import annotations

import calendar as civil_calendar
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.application.commands.liturgical_calendar import (
    CreateFeastEntryCommand,
    CreateLiturgicalObservanceCommand,
    UpdateFeastEntryCommand,
    UpdateLiturgicalObservanceCommand,
)
from src.domain.hagiography.models import Person
from src.domain.liturgy.models import (
    Feast,
    FeastRank,
    LiturgicalCalendar,
    LiturgicalObservance,
)

RANK_PRIORITY: dict[str, int] = {
    FeastRank.SOLEMNITY.value: 0,
    FeastRank.FEAST.value: 1,
    FeastRank.MEMORIAL.value: 2,
    FeastRank.OPT_MEMORIAL.value: 3,
    FeastRank.COMMEMORATION.value: 4,
}


class CalendarNotFoundError(ValueError):
    """Raised when an active calendar cannot be found."""


class FeastNotFoundError(ValueError):
    """Raised when a feast or its person cannot be found."""


class FeastConflictError(ValueError):
    """Raised when a target is already assigned to a calendar date."""


class ObservanceNotFoundError(ValueError):
    """Raised when a non-person liturgical observance cannot be found."""


class ObservanceConflictError(ValueError):
    """Raised when an observance slug is already in use."""


class CalendarService:
    """Read and mutate liturgical calendars inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_calendars(self) -> list[LiturgicalCalendar]:
        """Return all active liturgical calendars."""
        result = await self.db.execute(
            select(LiturgicalCalendar)
            .where(
                LiturgicalCalendar.deleted_at.is_(None),
                LiturgicalCalendar.is_active.is_(True),
            )
            .order_by(LiturgicalCalendar.scope.asc(), LiturgicalCalendar.name.asc())
        )
        return list(result.scalars().all())

    async def get_calendar(self, code: str) -> LiturgicalCalendar:
        """Resolve one active calendar by its stable code."""
        result = await self.db.execute(
            select(LiturgicalCalendar).where(
                LiturgicalCalendar.code == code,
                LiturgicalCalendar.deleted_at.is_(None),
                LiturgicalCalendar.is_active.is_(True),
            )
        )
        calendar = result.scalar_one_or_none()
        if calendar is None:
            raise CalendarNotFoundError(f"Nie znaleziono kalendarza: {code}")
        return calendar

    async def list_observances(self) -> list[LiturgicalObservance]:
        """Return active non-person observances for editorial and public views."""
        result = await self.db.execute(
            select(LiturgicalObservance)
            .where(LiturgicalObservance.deleted_at.is_(None))
            .order_by(LiturgicalObservance.title_pl.asc())
        )
        return list(result.scalars().all())

    async def get_observance(self, id_or_slug: uuid.UUID | str) -> LiturgicalObservance:
        """Resolve an active observance by UUID or stable public slug."""
        criterion = (
            LiturgicalObservance.id == id_or_slug
            if isinstance(id_or_slug, uuid.UUID)
            else LiturgicalObservance.slug == id_or_slug
        )
        result = await self.db.execute(
            select(LiturgicalObservance).where(
                criterion,
                LiturgicalObservance.deleted_at.is_(None),
            )
        )
        observance = result.scalar_one_or_none()
        if observance is None:
            raise ObservanceNotFoundError("Obchód liturgiczny nie istnieje")
        return observance

    async def _ensure_observance_slug_available(
        self, slug: str, *, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(LiturgicalObservance.id).where(LiturgicalObservance.slug == slug)
        if exclude_id is not None:
            query = query.where(LiturgicalObservance.id != exclude_id)
        if (await self.db.execute(query)).scalar_one_or_none() is not None:
            raise ObservanceConflictError("Slug obchodu liturgicznego jest już zajęty")

    async def create_observance(
        self, data: CreateLiturgicalObservanceCommand
    ) -> LiturgicalObservance:
        """Create a non-person observance without entering it into the person catalogue."""
        await self._ensure_observance_slug_available(data.slug)
        observance = LiturgicalObservance(**data.model_dump(mode="json"))
        self.db.add(observance)
        await self.db.flush()
        return await self.get_observance(observance.id)

    async def update_observance(
        self,
        observance_id: uuid.UUID,
        data: UpdateLiturgicalObservanceCommand,
    ) -> LiturgicalObservance:
        """Update editorial content of a non-person observance."""
        observance = await self.get_observance(observance_id)
        changes = data.model_dump(exclude_unset=True, mode="json")
        if slug := changes.get("slug"):
            await self._ensure_observance_slug_available(slug, exclude_id=observance.id)
        for field, value in changes.items():
            setattr(observance, field, value)
        await self.db.flush()
        return await self.get_observance(observance.id)

    async def delete_observance(self, observance_id: uuid.UUID) -> None:
        """Soft-delete an observance and its active calendar assignments."""
        observance = await self.get_observance(observance_id)
        now = datetime.now(UTC)
        await self.db.execute(
            update(Feast)
            .where(
                Feast.observance_id == observance.id,
                Feast.deleted_at.is_(None),
            )
            .values(is_primary=False, deleted_at=now, updated_at=now)
        )
        observance.deleted_at = now
        await self.db.flush()

    async def _calendar_codes(
        self,
        code: str,
        include_universal: bool,
        include_martyrology: bool,
    ) -> tuple[LiturgicalCalendar, list[str]]:
        selected = await self.get_calendar(code)
        codes = [selected.code]
        if include_universal and selected.code != "roman_universal":
            await self.get_calendar("roman_universal")
            codes.append("roman_universal")
        if include_martyrology and selected.code != "roman_martyrology":
            await self.get_calendar("roman_martyrology")
            codes.append("roman_martyrology")
        return selected, codes

    async def _query_fixed_entries(
        self,
        *,
        calendar_codes: list[str],
        month: int,
        day: int | None = None,
        public_only: bool = True,
    ) -> list[Feast]:
        query = (
            select(Feast)
            .join(Feast.calendar)
            .outerjoin(Feast.person)
            .outerjoin(Feast.observance)
            .where(
                Feast.deleted_at.is_(None),
                Feast.is_suppressed.is_(False),
                Feast.is_moveable.is_(False),
                Feast.month == month,
                LiturgicalCalendar.code.in_(calendar_codes),
                LiturgicalCalendar.deleted_at.is_(None),
                LiturgicalCalendar.is_active.is_(True),
                or_(
                    and_(
                        Feast.person_id.is_not(None),
                        Person.deleted_at.is_(None),
                    ),
                    and_(
                        Feast.observance_id.is_not(None),
                        LiturgicalObservance.deleted_at.is_(None),
                    ),
                ),
            )
            .options(
                joinedload(Feast.calendar),
                selectinload(Feast.person).selectinload(Person.images),
                selectinload(Feast.person).selectinload(Person.patronages),
                joinedload(Feast.observance),
            )
        )
        if day is not None:
            query = query.where(Feast.day == day)
        if public_only:
            query = query.where(
                or_(
                    and_(Feast.person_id.is_not(None), Person.status == "published"),
                    Feast.observance_id.is_not(None),
                )
            )

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    @staticmethod
    def _merge_and_sort(entries: list[Feast], selected_code: str) -> list[Feast]:
        """Prefer local assignments, deduplicate targets, then rank display order."""

        def calendar_priority(feast: Feast) -> int:
            return 0 if feast.calendar.code == selected_code else 1

        preferred = sorted(entries, key=calendar_priority)

        by_target: dict[tuple[str, uuid.UUID], Feast] = {}
        for feast in preferred:
            if feast.person_id is not None:
                target_key = ("person", feast.person_id)
            elif feast.observance_id is not None:
                target_key = ("observance", feast.observance_id)
            else:  # The database constraint prevents this; keep sorting defensive.
                continue
            by_target.setdefault(target_key, feast)

        def target_is_featured(feast: Feast) -> bool:
            if feast.person is not None:
                return feast.person.is_featured
            return bool(feast.observance and feast.observance.is_featured)

        def target_title(feast: Feast) -> str:
            if feast.person is not None:
                return feast.person.canonical_name
            return feast.observance.title_pl if feast.observance is not None else ""

        return sorted(
            by_target.values(),
            key=lambda feast: (
                0 if feast.is_primary else 1,
                calendar_priority(feast),
                0 if target_is_featured(feast) else 1,
                RANK_PRIORITY.get(feast.rank, 99),
                target_title(feast).casefold(),
            ),
        )

    async def get_day(
        self,
        value: date,
        *,
        calendar_code: str = "roman_pl",
        include_universal: bool = True,
        include_martyrology: bool = True,
    ) -> tuple[LiturgicalCalendar, list[Feast]]:
        """Return merged and ordered fixed commemorations for one date."""
        selected, codes = await self._calendar_codes(
            calendar_code,
            include_universal,
            include_martyrology,
        )
        entries = await self._query_fixed_entries(
            calendar_codes=codes,
            month=value.month,
            day=value.day,
        )
        return selected, self._merge_and_sort(entries, selected.code)

    async def get_month(
        self,
        *,
        year: int,
        month: int,
        calendar_code: str = "roman_pl",
        include_universal: bool = True,
        include_martyrology: bool = True,
    ) -> tuple[LiturgicalCalendar, dict[int, list[Feast]]]:
        """Return fixed-date commemorations grouped by day of month."""
        date(year, month, 1)
        selected, codes = await self._calendar_codes(
            calendar_code,
            include_universal,
            include_martyrology,
        )
        entries = await self._query_fixed_entries(calendar_codes=codes, month=month)
        grouped: dict[int, list[Feast]] = defaultdict(list)
        for feast in entries:
            if feast.day is not None and feast.day <= civil_calendar.monthrange(year, month)[1]:
                grouped[feast.day].append(feast)
        return selected, {
            day: self._merge_and_sort(day_entries, selected.code)
            for day, day_entries in grouped.items()
        }

    async def _clear_primary(
        self, calendar_id: uuid.UUID, month: int, day: int, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = (
            update(Feast)
            .where(
                Feast.calendar_id == calendar_id,
                Feast.month == month,
                Feast.day == day,
                Feast.deleted_at.is_(None),
                Feast.is_primary.is_(True),
            )
            .values(is_primary=False, updated_at=datetime.now(UTC))
        )
        if exclude_id is not None:
            query = query.where(Feast.id != exclude_id)
        await self.db.execute(query)

    async def _assert_unique_assignment(
        self,
        *,
        person_id: uuid.UUID | None,
        observance_id: uuid.UUID | None,
        calendar_id: uuid.UUID,
        month: int,
        day: int,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        target_criterion = (
            Feast.person_id == person_id
            if person_id is not None
            else Feast.observance_id == observance_id
        )
        query = select(Feast.id).where(
            target_criterion,
            Feast.calendar_id == calendar_id,
            Feast.month == month,
            Feast.day == day,
            Feast.deleted_at.is_(None),
        )
        if exclude_id is not None:
            query = query.where(Feast.id != exclude_id)
        if (await self.db.execute(query)).scalar_one_or_none() is not None:
            raise FeastConflictError("Ten cel jest już przypisany do tej daty i kalendarza")

    async def get_entry(self, entry_id: uuid.UUID) -> Feast:
        """Load one active entry with all public response relationships."""
        result = await self.db.execute(
            select(Feast)
            .where(Feast.id == entry_id, Feast.deleted_at.is_(None))
            .options(
                joinedload(Feast.calendar),
                selectinload(Feast.person).selectinload(Person.images),
                selectinload(Feast.person).selectinload(Person.patronages),
                joinedload(Feast.observance),
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            raise FeastNotFoundError("Wpis kalendarza nie istnieje")
        return entry

    async def list_person_entries(self, person_id: uuid.UUID) -> list[Feast]:
        """Return all active liturgical calendar assignments for one person."""
        person = await self.db.get(Person, person_id)
        if person is None or person.deleted_at is not None:
            raise FeastNotFoundError("Osoba nie istnieje")

        result = await self.db.execute(
            select(Feast)
            .join(Feast.calendar)
            .where(
                Feast.person_id == person_id,
                Feast.deleted_at.is_(None),
                LiturgicalCalendar.deleted_at.is_(None),
                LiturgicalCalendar.is_active.is_(True),
            )
            .options(
                joinedload(Feast.calendar),
                selectinload(Feast.person).selectinload(Person.images),
                selectinload(Feast.person).selectinload(Person.patronages),
                joinedload(Feast.observance),
            )
            .order_by(
                LiturgicalCalendar.scope.asc(),
                LiturgicalCalendar.name.asc(),
                Feast.month.asc(),
                Feast.day.asc(),
            )
        )
        return list(result.scalars().unique().all())

    async def create_entry(self, data: CreateFeastEntryCommand) -> Feast:
        """Create a fixed commemoration and maintain the one-primary invariant."""
        selected = await self.get_calendar(data.calendar_code)
        person: Person | None = None
        observance: LiturgicalObservance | None = None
        if data.person_id is not None:
            person = await self.db.get(Person, data.person_id)
            if person is None or person.deleted_at is not None:
                raise FeastNotFoundError("Osoba nie istnieje")
        elif data.observance_id is not None:
            try:
                observance = await self.get_observance(data.observance_id)
            except ObservanceNotFoundError as exc:
                raise FeastNotFoundError(str(exc)) from exc

        await self._assert_unique_assignment(
            person_id=person.id if person else None,
            observance_id=observance.id if observance else None,
            calendar_id=selected.id,
            month=data.month,
            day=data.day,
        )
        if data.is_primary:
            await self._clear_primary(selected.id, data.month, data.day)

        entry = Feast(
            person_id=person.id if person else None,
            observance_id=observance.id if observance else None,
            calendar_id=selected.id,
            month=data.month,
            day=data.day,
            day_of_year=date(2000, data.month, data.day).timetuple().tm_yday,
            is_moveable=False,
            rank=data.rank.value,
            liturgical_color=data.liturgical_color.value if data.liturgical_color else None,
            is_primary=data.is_primary,
            is_suppressed=data.is_suppressed,
            notes=data.notes,
            source_title=data.source_title,
            source_url=str(data.source_url) if data.source_url else None,
        )
        self.db.add(entry)
        await self.db.flush()
        return await self.get_entry(entry.id)

    async def update_entry(self, entry_id: uuid.UUID, data: UpdateFeastEntryCommand) -> Feast:
        """Update one commemoration and re-check its date-level invariants."""
        entry = await self.get_entry(entry_id)
        changes = data.model_dump(exclude_unset=True, mode="json")

        calendar_code = changes.pop("calendar_code", None)
        selected = await self.get_calendar(calendar_code) if calendar_code else entry.calendar
        month = changes.pop("month", entry.month)
        day = changes.pop("day", entry.day)
        if month is None or day is None:
            raise ValueError("Wpis stały wymaga miesiąca i dnia")
        date(2000, month, day)

        await self._assert_unique_assignment(
            person_id=entry.person_id,
            observance_id=entry.observance_id,
            calendar_id=selected.id,
            month=month,
            day=day,
            exclude_id=entry.id,
        )
        if changes.get("is_primary") is True:
            await self._clear_primary(selected.id, month, day, exclude_id=entry.id)

        entry.calendar_id = selected.id
        entry.month = month
        entry.day = day
        entry.day_of_year = date(2000, month, day).timetuple().tm_yday
        for field, value in changes.items():
            setattr(entry, field, value)
        await self.db.flush()
        return await self.get_entry(entry.id)

    async def delete_entry(self, entry_id: uuid.UUID) -> None:
        """Soft-delete a commemoration."""
        entry = await self.get_entry(entry_id)
        entry.is_primary = False
        entry.deleted_at = datetime.now(UTC)
        await self.db.flush()
