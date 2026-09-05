"""Application commands for liturgical observances and calendar entries."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field, HttpUrl, model_validator

from src.domain.hagiography.models import LiturgicalColor
from src.domain.liturgy.models import FeastRank, ObservanceType


class CreateLiturgicalObservanceCommand(BaseModel):
    """Validated input for a non-person liturgical observance."""

    slug: str = Field(..., min_length=2, max_length=300, pattern=r"^[a-z0-9-]+$")
    title_pl: str = Field(..., min_length=2, max_length=500)
    title_en: str | None = Field(None, max_length=500)
    latin_title: str | None = Field(None, max_length=500)
    observance_type: ObservanceType
    summary_pl: str | None = None
    description_pl: str | None = None
    iconographic_attributes: str | None = None
    is_featured: bool = False


class UpdateLiturgicalObservanceCommand(BaseModel):
    """Validated patch for a non-person liturgical observance."""

    slug: str | None = Field(None, min_length=2, max_length=300, pattern=r"^[a-z0-9-]+$")
    title_pl: str | None = Field(None, min_length=2, max_length=500)
    title_en: str | None = Field(None, max_length=500)
    latin_title: str | None = Field(None, max_length=500)
    observance_type: ObservanceType | None = None
    summary_pl: str | None = None
    description_pl: str | None = None
    iconographic_attributes: str | None = None
    is_featured: bool | None = None


class CreateFeastEntryCommand(BaseModel):
    """Validated input for a fixed-date commemoration."""

    person_id: uuid.UUID | None = None
    observance_id: uuid.UUID | None = None
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
    def validate_fixed_date(self) -> CreateFeastEntryCommand:
        """Validate the date and require exactly one kind of calendar target."""
        date(2000, self.month, self.day)
        if (self.person_id is None) == (self.observance_id is None):
            raise ValueError("Wpis musi wskazywać dokładnie jedną osobę albo obchód liturgiczny")
        return self


class UpdateFeastEntryCommand(BaseModel):
    """Validated patch for a fixed-date commemoration."""

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
