"""Application service for liturgical calendar mutations."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select, update

from src.application.commands.liturgical_calendar import (
    CreateFeastEntryCommand,
    CreateLiturgicalObservanceCommand,
    UpdateFeastEntryCommand,
    UpdateLiturgicalObservanceCommand,
)
from src.application.services.calendar_query_service import (
    RANK_PRIORITY,
    CalendarNotFoundError,
    CalendarQueryService,
    FeastNotFoundError,
    ObservanceNotFoundError,
)
from src.domain.hagiography.models import Person
from src.domain.liturgy.models import Feast, LiturgicalObservance

__all__ = [
    "CalendarNotFoundError",
    "CalendarService",
    "FeastConflictError",
    "FeastNotFoundError",
    "ObservanceConflictError",
    "ObservanceNotFoundError",
    "RANK_PRIORITY",
]


class FeastConflictError(ValueError):
    """Raised when a target is already assigned to a calendar date."""


class ObservanceConflictError(ValueError):
    """Raised when an observance slug is already in use."""


class CalendarService(CalendarQueryService):
    """Mutate liturgical calendars with a legacy-compatible read interface."""

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

    async def _clear_primary(
        self,
        calendar_id: uuid.UUID,
        month: int,
        day: int,
        exclude_id: uuid.UUID | None = None,
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
