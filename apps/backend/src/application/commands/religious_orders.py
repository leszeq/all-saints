"""Application commands for religious communities and memberships."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, HttpUrl

from src.domain.geography.models import (
    OrderCharism,
    OrderMembershipType,
    ReligiousCommunityType,
)


class CreateReligiousOrderCommand(BaseModel):
    """Validated input required to create a religious community."""

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


class UpdateReligiousOrderCommand(BaseModel):
    """Validated patch for editable religious-community fields."""

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


class AddReligiousOrderMembershipCommand(BaseModel):
    """Validated input for attaching a person to a religious community."""

    person_id: uuid.UUID
    entry_date: str | None = Field(None, max_length=50)
    exit_date: str | None = Field(None, max_length=50)
    is_founder: bool = False
    membership_type: OrderMembershipType = OrderMembershipType.MEMBER
    notes: str | None = None
