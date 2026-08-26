"""Pydantic schemas for liturgical calendars and fixed-date commemorations."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

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


class FeastEntryCreateSchema(BaseModel):
    """Create a fixed-date commemoration in a selected calendar."""

    person_id: uuid.UUID
    calendar_code: str = Field(default="roman_pl", min_length=2, max_length=50)
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    rank: FeastRank = FeastRank.MEMORIAL
    liturgical_color: LiturgicalColor | None = None
    is_primary: bool = False
    is_suppressed: bool = False
    notes: str | None = None
    source_title: str | None = Field(None, max_length=500)
    source_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_fixed_date(self) -> FeastEntryCreateSchema:
        """Validate month/day against a leap year so 29 February remains legal."""
        date(2000, self.month, self.day)
        return self


class FeastEntryUpdateSchema(BaseModel):
    """Editable fields of a commemoration."""

    calendar_code: str | None = Field(None, min_length=2, max_length=50)
    month: int | None = Field(None, ge=1, le=12)
    day: int | None = Field(None, ge=1, le=31)
    rank: FeastRank | None = None
    liturgical_color: LiturgicalColor | None = None
    is_primary: bool | None = None
    is_suppressed: bool | None = None
    notes: str | None = None
    source_title: str | None = Field(None, max_length=500)
    source_url: HttpUrl | None = None


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
    person: CalendarPersonSchema
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
