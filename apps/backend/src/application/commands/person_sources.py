"""Validated inputs for assigning editorial sources to people."""

from __future__ import annotations

import uuid

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class CreatePersonSourceCommand(BaseModel):
    """Attach exactly one bibliographic or historical source to a person."""

    bibliography_id: uuid.UUID | None = None
    historical_source_id: uuid.UUID | None = None
    page_reference: str | None = Field(None, max_length=200)
    quote: str | None = None
    relevance_score: int | None = Field(None, ge=1, le=5)
    is_primary: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def validate_single_source(self) -> CreatePersonSourceCommand:
        if (self.bibliography_id is None) == (self.historical_source_id is None):
            raise ValueError("Wybierz dokładnie jedno źródło")
        return self


class CreatePersonWebSourceCommand(BaseModel):
    """Create or reuse one website source and attach it atomically."""

    title: str = Field(..., min_length=2, max_length=1000)
    url: AnyHttpUrl
    authors: str | None = Field(None, max_length=1000)
    publisher: str | None = Field(None, max_length=500)
    year: int | None = Field(None, ge=1, le=2100)
    language: str | None = Field(default="pl", max_length=10)
    reliability_score: int | None = Field(None, ge=1, le=5)
    page_reference: str | None = Field(None, max_length=200)
    relevance_score: int | None = Field(None, ge=1, le=5)
    is_primary: bool = False
    notes: str | None = None
