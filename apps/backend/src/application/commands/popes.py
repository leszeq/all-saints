"""Validated application commands for pope catalogue entries."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CreatePopeCommand(BaseModel):
    """Input required to create a pope catalogue entry."""

    papal_name: str = Field(..., min_length=2, max_length=300)
    person_id: uuid.UUID | None = None
    pontificate_start: str | None = Field(None, max_length=50)
    pontificate_end: str | None = Field(None, max_length=50)
    pontificate_start_year: int | None = None
    pontificate_end_year: int | None = None
    regnal_number: int | None = None
    birth_name: str | None = Field(None, max_length=300)
    nationality_id: uuid.UUID | None = None
    description: str | None = None
