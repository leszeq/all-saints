"""
Pydantic v2 schemas for Religious Orders and Popes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.domain.geography.models import (
    OrderCharism,
    ReligiousCommunityType,
)
from src.domain.hagiography.models import PersonType
from src.presentation.api.v1.persons.schemas import PersonAvatarSchema

# ==============================================================================
# RELIGIOUS ORDER SCHEMAS
# ==============================================================================


class OrderMembershipType(StrEnum):
    """A person's form of belonging to a religious family."""

    FOUNDER = "founder"
    MONK = "monk"
    FRIAR = "friar"
    NUN = "nun"
    SISTER = "sister"
    LAY_MEMBER = "lay_member"
    SPIRITUAL_PATRON = "spiritual_patron"
    MEMBER = "member"


class ReligiousOrderCreateSchema(BaseModel):
    slug: str = Field(..., min_length=2, max_length=500, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=2, max_length=500)
    name_la: str | None = Field(None, max_length=500)
    name_local: str | None = Field(None, max_length=500)
    abbreviation: str | None = Field(None, max_length=20)
    community_type: ReligiousCommunityType = ReligiousCommunityType.RELIGIOUS_ORDER
    spiritual_family: str | None = Field(None, max_length=80)
    founded_year: int | None = None
    founded_place_id: uuid.UUID | None = None
    founder_id: uuid.UUID | None = None
    founder_name: str | None = Field(None, max_length=500)
    suppressed_year: int | None = None
    charism: OrderCharism | None = None
    description: str | None = None
    description_en: str | None = None
    history: str | None = None
    mission: str | None = None
    motto: str | None = Field(None, max_length=300)
    website_url: HttpUrl | None = None
    source_title: str | None = Field(None, max_length=500)
    source_url: HttpUrl | None = None
    papal_approval_year: int | None = None
    is_suppressed: bool = False
    is_featured: bool = False
    sort_order: int = 0


class ReligiousOrderUpdateSchema(BaseModel):
    slug: str | None = Field(None, min_length=2, max_length=500, pattern=r"^[a-z0-9-]+$")
    name: str | None = Field(None, min_length=2, max_length=500)
    name_la: str | None = None
    name_local: str | None = None
    abbreviation: str | None = None
    community_type: ReligiousCommunityType | None = None
    spiritual_family: str | None = None
    founded_year: int | None = None
    founded_place_id: uuid.UUID | None = None
    founder_id: uuid.UUID | None = None
    founder_name: str | None = None
    suppressed_year: int | None = None
    charism: OrderCharism | None = None
    description: str | None = None
    description_en: str | None = None
    history: str | None = None
    mission: str | None = None
    motto: str | None = None
    website_url: HttpUrl | None = None
    source_title: str | None = None
    source_url: HttpUrl | None = None
    papal_approval_year: int | None = None
    is_suppressed: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None


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


class ReligiousOrderMembershipCreateSchema(BaseModel):
    """Attach one person to an order or congregation."""

    person_id: uuid.UUID
    entry_date: str | None = Field(None, max_length=50)
    exit_date: str | None = Field(None, max_length=50)
    is_founder: bool = False
    membership_type: OrderMembershipType = OrderMembershipType.MEMBER
    notes: str | None = None


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
