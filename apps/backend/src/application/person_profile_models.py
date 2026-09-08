"""Versioned, portable JSON contract for a complete person profile."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from src.application.commands.persons import PersonCreateSchema
from src.domain.geography.models import OrderMembershipType
from src.domain.hagiography.models import LiturgicalColor
from src.domain.liturgy.models import FeastRank
from src.domain.sources.models import SourceType

PERSON_PROFILE_SCHEMA_VERSION: Literal[1] = 1


class PortablePersonData(PersonCreateSchema):
    """Editable person fields exported without database-owned identifiers."""

    model_config = ConfigDict(extra="forbid")


class PortableOrderMembership(BaseModel):
    """Order membership resolved by the community's stable slug during import."""

    order_slug: str = Field(..., min_length=2, max_length=500)
    entry_date: str | None = Field(None, max_length=50)
    exit_date: str | None = Field(None, max_length=50)
    is_founder: bool = False
    membership_type: OrderMembershipType = OrderMembershipType.MEMBER
    notes: str | None = None


class PortableFeastEntry(BaseModel):
    """Calendar assignment resolved by calendar code during import."""

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

    model_config = ConfigDict(extra="forbid")


class PortableSourceLink(BaseModel):
    """Editorial metadata attached to one source reference."""

    page_reference: str | None = Field(None, max_length=200)
    quote: str | None = None
    relevance_score: int | None = Field(None, ge=1, le=5)
    is_primary: bool = False
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class PortableBibliography(BaseModel):
    """Bibliographic data copied by value rather than by database UUID."""

    source_type: SourceType = SourceType.BOOK
    title: str = Field(..., min_length=2, max_length=1000)
    subtitle: str | None = Field(None, max_length=500)
    authors: str | None = Field(None, max_length=1000)
    editor: str | None = Field(None, max_length=500)
    publisher: str | None = Field(None, max_length=500)
    place_of_publication: str | None = Field(None, max_length=300)
    year: int | None = None
    edition: str | None = Field(None, max_length=100)
    volume: str | None = Field(None, max_length=100)
    pages: str | None = Field(None, max_length=100)
    isbn: str | None = Field(None, max_length=20)
    issn: str | None = Field(None, max_length=20)
    doi: str | None = Field(None, max_length=500)
    url: str | None = Field(None, max_length=2000)
    language: str | None = Field(None, max_length=10)
    abstract: str | None = None
    reliability_score: int | None = Field(None, ge=1, le=5)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class PortableHistoricalSource(BaseModel):
    """Historical source copied by value rather than by database UUID."""

    title: str = Field(..., min_length=2, max_length=1000)
    original_title: str | None = Field(None, max_length=1000)
    source_type: SourceType = SourceType.MANUSCRIPT
    repository: str | None = Field(None, max_length=500)
    call_number: str | None = Field(None, max_length=200)
    date_range: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=100)
    description: str | None = None
    digitization_url: str | None = Field(None, max_length=2000)
    is_digitized: bool = False

    model_config = ConfigDict(extra="forbid")


class PortablePersonSource(BaseModel):
    """Exactly one embedded bibliography or historical source and its link."""

    kind: Literal["bibliography", "historical"]
    bibliography: PortableBibliography | None = None
    historical_source: PortableHistoricalSource | None = None
    link: PortableSourceLink = Field(default_factory=PortableSourceLink)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_source_kind(self) -> PortablePersonSource:
        if self.kind == "bibliography" and (
            self.bibliography is None or self.historical_source is not None
        ):
            raise ValueError("Źródło bibliograficzne wymaga wyłącznie pola bibliography")
        if self.kind == "historical" and (
            self.historical_source is None or self.bibliography is not None
        ):
            raise ValueError("Źródło historyczne wymaga wyłącznie pola historical_source")
        return self


class PersonProfileDocument(BaseModel):
    """Publicly documented JSON envelope supported by import and export."""

    schema_version: Literal[1] = PERSON_PROFILE_SCHEMA_VERSION
    exported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_person_id: uuid.UUID | None = None
    source_slug: str | None = None
    source_status: str | None = None
    profile: PortablePersonData
    orders: list[PortableOrderMembership] = Field(default_factory=list)
    feasts: list[PortableFeastEntry] = Field(default_factory=list)
    sources: list[PortablePersonSource] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PersonProfileValidationResult(BaseModel):
    """Business validation result shown before an import is persisted."""

    can_import: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalized_document: PersonProfileDocument
