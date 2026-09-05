"""Pydantic schemas for liturgical calendars and fixed-date commemorations."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.liturgical_calendar import (
    CreateFeastEntryCommand,
    CreateLiturgicalObservanceCommand,
    UpdateFeastEntryCommand,
    UpdateLiturgicalObservanceCommand,
)
from src.domain.hagiography.models import Gender, LiturgicalColor, PersonType
from src.domain.liturgy.models import CalendarScope, FeastRank
from src.presentation.api.v1.persons.schemas import (
    PersonAvatarSchema,
    PersonPatronageSchema,
)


class LiturgicalCalendarSchema(BaseModel):
    """Calendar metadata exposed with every commemoration."""

    id: uuid.UUID
    code: str
    name: str
    rite: str
    scope: CalendarScope
    description: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CalendarPersonSchema(BaseModel):
    """Compact public person data used by calendar cards."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    person_type: PersonType
    gender: Gender
    birth_year: int | None = None
    death_year: int | None = None
    summary_pl: str | None = None
    is_featured: bool
    avatar: PersonAvatarSchema | None = None
    patronages: list[PersonPatronageSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class LiturgicalObservanceBaseSchema(CreateLiturgicalObservanceCommand):
    """Shared editorial content for a non-person liturgical observance."""


class LiturgicalObservanceCreateSchema(LiturgicalObservanceBaseSchema):
    """Create a Marian, Lord's, or other non-person observance."""


class LiturgicalObservanceUpdateSchema(UpdateLiturgicalObservanceCommand):
    """Editable fields of a non-person observance."""


class LiturgicalObservanceSchema(LiturgicalObservanceBaseSchema):
    """Public representation of a non-person liturgical observance."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeastEntryCreateSchema(CreateFeastEntryCommand):
    """Create a fixed-date commemoration in a selected calendar."""


class FeastEntryUpdateSchema(UpdateFeastEntryCommand):
    """Editable fields of a commemoration."""


class FeastEntrySchema(BaseModel):
    """Public commemoration with its person, calendar, and provenance."""

    id: uuid.UUID
    month: int | None
    day: int | None
    date_note: str | None = None
    is_moveable: bool
    rank: FeastRank
    liturgical_color: LiturgicalColor | None = None
    is_primary: bool
    notes: str | None = None
    source_title: str | None = None
    source_url: str | None = None
    person: CalendarPersonSchema | None = None
    observance: LiturgicalObservanceSchema | None = None
    calendar: LiturgicalCalendarSchema
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CalendarDaySchema(BaseModel):
    """All commemorations for one civil date after calendar merging."""

    date: date
    calendar_code: str
    calendar_name: str
    includes_universal: bool
    includes_martyrology: bool
    primary: FeastEntrySchema | None
    entries: list[FeastEntrySchema]
    total: int


class CalendarMonthSchema(BaseModel):
    """Every day of a month, including days without assigned people."""

    year: int
    month: int
    calendar_code: str
    calendar_name: str
    includes_universal: bool
    includes_martyrology: bool
    days: list[CalendarDaySchema]
