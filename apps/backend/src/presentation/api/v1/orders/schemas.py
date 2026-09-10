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
from src.presentation.api.v1.popes.schemas import (
    PopeCreateSchema as PopeCreateSchema,
)
from src.presentation.api.v1.popes.schemas import (
    PopeSchema as PopeSchema,
)
from src.presentation.api.v1.popes.schemas import (
    PopeUpdateSchema as PopeUpdateSchema,
)

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
