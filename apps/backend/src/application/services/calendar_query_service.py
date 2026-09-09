"""Read model for liturgical calendars and daily commemorations."""

from __future__ import annotations

import calendar as civil_calendar
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

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


class ObservanceNotFoundError(ValueError):
    """Raised when a non-person liturgical observance cannot be found."""


class CalendarQueryService:
    """Query liturgical calendars without exposing mutation operations."""

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
