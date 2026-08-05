"""
Pydantic v2 schemas for Religious Orders and Popes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from src.domain.geography.models import OrderCharism


# ==============================================================================
# RELIGIOUS ORDER SCHEMAS
# ==============================================================================


class ReligiousOrderCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)
    name_la: str | None = Field(None, max_length=500)
    name_local: str | None = Field(None, max_length=500)
    abbreviation: str | None = Field(None, max_length=20)
    founded_year: int | None = None
    founded_place_id: uuid.UUID | None = None
    founder_id: uuid.UUID | None = None
    suppressed_year: int | None = None
    charism: OrderCharism | None = None
    description: str | None = None
    description_en: str | None = None
    papal_approval_year: int | None = None
    is_suppressed: bool = False


class ReligiousOrderUpdateSchema(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=500)
    name_la: str | None = None
    name_local: str | None = None
    abbreviation: str | None = None
    founded_year: int | None = None
    founded_place_id: uuid.UUID | None = None
    founder_id: uuid.UUID | None = None
    suppressed_year: int | None = None
    charism: OrderCharism | None = None
    description: str | None = None
    description_en: str | None = None
    papal_approval_year: int | None = None
    is_suppressed: bool | None = None


class ReligiousOrderSchema(ReligiousOrderCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# POPE SCHEMAS
# ==============================================================================


class PopeCreateSchema(BaseModel):
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
