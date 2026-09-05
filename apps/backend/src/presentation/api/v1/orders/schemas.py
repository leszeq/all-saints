"""
Pydantic v2 schemas for Religious Orders and Popes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.religious_orders import (
    AddReligiousOrderMembershipCommand,
    CreateReligiousOrderCommand,
    UpdateReligiousOrderCommand,
)
from src.domain.geography.models import OrderMembershipType
from src.domain.hagiography.models import PersonType
from src.presentation.api.v1.persons.schemas import PersonAvatarSchema

# ==============================================================================
# RELIGIOUS ORDER SCHEMAS
# ==============================================================================


class ReligiousOrderCreateSchema(CreateReligiousOrderCommand):
    pass


class ReligiousOrderUpdateSchema(UpdateReligiousOrderCommand):
    pass


class ReligiousOrderSchema(ReligiousOrderCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OrderMemberPersonSchema(BaseModel):
    """Compact person card embedded in an order profile."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    person_type: PersonType
    birth_year: int | None = None
    death_year: int | None = None
    summary_pl: str | None = None
    avatar: PersonAvatarSchema | None = None

    model_config = ConfigDict(from_attributes=True)


class ReligiousOrderMembershipSchema(BaseModel):
    """Membership data shown next to a linked saint."""

    entry_date: str | None = None
    exit_date: str | None = None
    is_founder: bool
    membership_type: OrderMembershipType
    notes: str | None = None
    person: OrderMemberPersonSchema

    model_config = ConfigDict(from_attributes=True)


class ReligiousOrderDetailSchema(ReligiousOrderSchema):
    """Complete public order profile with linked people."""

    members: list[ReligiousOrderMembershipSchema] = Field(default_factory=list)


class ReligiousOrderMembershipCreateSchema(AddReligiousOrderMembershipCommand):
    """Attach one person to an order or congregation."""


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
