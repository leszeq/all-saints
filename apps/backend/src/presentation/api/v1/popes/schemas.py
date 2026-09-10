"""Transport schemas for pope catalogue entries."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.popes import CreatePopeCommand


class PopeCreateSchema(CreatePopeCommand):
    pass


class PopeUpdateSchema(BaseModel):
    papal_name: str | None = Field(None, min_length=2, max_length=300)
    person_id: uuid.UUID | None = None
    pontificate_start: str | None = None
    pontificate_end: str | None = None
    pontificate_start_year: int | None = None
    pontificate_end_year: int | None = None
    regnal_number: int | None = None
    birth_name: str | None = None
    nationality_id: uuid.UUID | None = None
    description: str | None = None


class PopeSchema(PopeCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
