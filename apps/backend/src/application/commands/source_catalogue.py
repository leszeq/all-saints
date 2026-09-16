"""Validated application inputs for source catalogue records."""

from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, Field

from src.domain.sources.models import SourceType


class CreateBibliographyCommand(BaseModel):
    """Create a bibliographic or web source record."""

    source_type: SourceType = Field(default=SourceType.BOOK)
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
    url: AnyHttpUrl | None = None
    language: str | None = Field(None, max_length=10)
    abstract: str | None = None
    reliability_score: int | None = Field(None, ge=1, le=5)
    notes: str | None = None


class CreateHistoricalSourceCommand(BaseModel):
    """Create a primary historical-source record."""

    title: str = Field(..., min_length=2, max_length=1000)
    original_title: str | None = Field(None, max_length=1000)
    source_type: SourceType = Field(default=SourceType.MANUSCRIPT)
    repository: str | None = Field(None, max_length=500)
    call_number: str | None = Field(None, max_length=200)
    date_range: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=100)
    description: str | None = None
    digitization_url: AnyHttpUrl | None = None
    is_digitized: bool = False


class UpdateBibliographyCommand(BaseModel):
    """Partial update of an existing bibliographic record."""

    source_type: SourceType | None = None
    title: str | None = Field(None, min_length=2, max_length=1000)
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
    url: AnyHttpUrl | None = None
    url_access_date: str | None = Field(None, max_length=50)
    language: str | None = Field(None, max_length=10)
    abstract: str | None = None
    reliability_score: int | None = Field(None, ge=1, le=5)
    notes: str | None = None


class UpdateHistoricalSourceCommand(BaseModel):
    """Partial update of an existing primary historical source."""

    title: str | None = Field(None, min_length=2, max_length=1000)
    original_title: str | None = Field(None, max_length=1000)
    source_type: SourceType | None = None
    repository: str | None = Field(None, max_length=500)
    call_number: str | None = Field(None, max_length=200)
    date_range: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=100)
    description: str | None = None
    digitization_url: AnyHttpUrl | None = None
    is_digitized: bool | None = None
