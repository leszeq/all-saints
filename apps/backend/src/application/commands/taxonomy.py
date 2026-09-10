"""Validated application commands for taxonomy reference data."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CreateCategoryCommand(BaseModel):
    """Input required to create a taxonomy category."""

    name_pl: str = Field(..., min_length=2, max_length=300)
    name_en: str = Field(..., min_length=2, max_length=300)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class CreateTagCommand(BaseModel):
    """Input required to create a taxonomy tag."""

    name_pl: str = Field(..., min_length=2, max_length=200)
    name_en: str = Field(..., min_length=2, max_length=200)
    color: str | None = Field(None, max_length=7, description="Hex color e.g. #FF5733")
