"""Pydantic v2 schemas for the Person HTTP API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.application import person_models
from src.application.commands import persons as person_commands
from src.domain.hagiography.models import (
    Era,
    Gender,
    LiturgicalColor,
    PersonNameKind,
    PersonType,
    PublicationStatus,
)
from src.presentation.api.v1.sources.public_schemas import PublicPersonSourceSchema

# Input schemas are owned by the application layer and re-exported here to keep
# existing API imports and OpenAPI component names stable.
PersonAliasInputSchema = person_commands.PersonAliasInputSchema
PersonAvatarInputSchema = person_commands.PersonAvatarInputSchema
PersonBaseSchema = person_commands.PersonBaseSchema
PersonBeatificationInputSchema = person_commands.PersonBeatificationInputSchema
PersonCanonizationInputSchema = person_commands.PersonCanonizationInputSchema
PersonCreateSchema = person_commands.PersonCreateSchema
PersonPatronageInputSchema = person_commands.PersonPatronageInputSchema
PersonUpdateSchema = person_commands.PersonUpdateSchema
PersonAvatarSchema = person_models.PersonAvatarSchema
PersonLastEditorSchema = person_models.PersonLastEditorSchema
PersonLocalizedContentSchema = person_models.PersonLocalizedContentSchema
PersonLocalizedSummarySchema = person_models.PersonLocalizedSummarySchema


class PersonPatronageSchema(BaseModel):
    """Patronage returned on public person lists and profiles."""

    id: uuid.UUID
    patronage_type: str
    name_pl: str
    name_en: str | None = None
    description: str | None = None
    is_official: bool

    model_config = ConfigDict(from_attributes=True)


class PersonAliasSchema(BaseModel):
    """Searchable alternative name returned on a person profile."""

    id: uuid.UUID
    value: str
    normalized_value: str
    language_code: str
    kind: PersonNameKind

    model_config = ConfigDict(from_attributes=True)


class PersonListItemSchema(BaseModel):
    """Lightweight schema for paginated lists."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    canonical_name_en: str | None = None
    latin_name: str | None = None
    person_type: PersonType
    status: PublicationStatus
    gender: Gender
    era: Era | None = None
    birth_year: int | None = None
    death_year: int | None = None
    summary_pl: str | None = None
    iconographic_attributes: str | None = None
    patronages: list[PersonPatronageSchema] = Field(default_factory=list)
    liturgical_color: LiturgicalColor | None = None
    is_featured: bool
    avatar: PersonAvatarSchema | None = None
    localized_content: PersonLocalizedSummarySchema | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PersonStateOfLifeSchema(BaseModel):
    """State-of-life label embedded in a person detail response."""

    id: uuid.UUID
    name_pl: str
    name_en: str
    name_la: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonReligiousCommunitySchema(BaseModel):
    """Religious community linked from a public person profile."""

    id: uuid.UUID
    slug: str
    name: str
    abbreviation: str | None = None
    community_type: str
    spiritual_family: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonOrderMembershipSchema(BaseModel):
    """A person's documented membership in a religious community."""

    entry_date: str | None = None
    exit_date: str | None = None
    is_founder: bool
    membership_type: str
    notes: str | None = None
    order: PersonReligiousCommunitySchema

    model_config = ConfigDict(from_attributes=True)


class PersonBeatificationSchema(BaseModel):
    """Beatification facts shown on a person profile when documented."""

    id: uuid.UUID
    beatification_date: str | None = None
    beatification_year: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonCanonizationSchema(BaseModel):
    """Canonization facts shown on a person profile when documented."""

    id: uuid.UUID
    canonization_date: str | None = None
    canonization_year: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonDetailSchema(PersonListItemSchema):
    """Complete detail schema for single record view."""

    localized_content: PersonLocalizedContentSchema | None = None

    latin_name: str | None = None
    original_name: str | None = None
    surnames: str | None = None
    religious_name: str | None = None
    epithets: list[str] | None = None
    century: int | None = None

    birth_date: str | None = None
    death_date: str | None = None

    birth_place_id: uuid.UUID | None = None
    death_place_id: uuid.UUID | None = None
    birth_country_id: uuid.UUID | None = None
    death_country_id: uuid.UUID | None = None
    nationality_id: uuid.UUID | None = None
    state_of_life_id: uuid.UUID | None = None
    state_of_life: PersonStateOfLifeSchema | None = None
    aliases: list[PersonAliasSchema] = Field(default_factory=list)
    patronages: list[PersonPatronageSchema] = Field(default_factory=list)
    orders: list[PersonOrderMembershipSchema] = Field(default_factory=list)
    sources: list[PublicPersonSourceSchema] = Field(default_factory=list)
    beatification: PersonBeatificationSchema | None = None
    canonization: PersonCanonizationSchema | None = None

    biography_pl: str | None = None
    summary_en: str | None = None
    biography_en: str | None = None

    iconographic_attributes: str | None = None
    prayers: str | None = None
    works: str | None = None

    version: int
    external_ids: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonListResponseSchema(BaseModel):
    """Paginated response wrapper."""

    items: list[PersonListItemSchema]
    total: int
    page: int
    per_page: int
    pages: int


class PersonFacetCountSchema(BaseModel):
    """Count for one relational discovery value."""

    id: uuid.UUID
    count: int


class PersonFacetCountsSchema(BaseModel):
    """Counts calculated from the same published set as the person catalogue."""

    total: int
    orders: list[PersonFacetCountSchema] = Field(default_factory=list)
    occupations: list[PersonFacetCountSchema] = Field(default_factory=list)
    birth_countries: list[PersonFacetCountSchema] = Field(default_factory=list)
    death_countries: list[PersonFacetCountSchema] = Field(default_factory=list)
    nationalities: list[PersonFacetCountSchema] = Field(default_factory=list)


class PublicIndexItemSchema(BaseModel):
    """Minimal public profile URL projection for crawlers."""

    id: uuid.UUID
    slug: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicIndexResponseSchema(BaseModel):
    """Cursor page of public profile URLs."""

    items: list[PublicIndexItemSchema]
    next_cursor: str | None = None


class PersonAdminListItemSchema(PersonListItemSchema):
    """Person row enriched with internal editorial audit information."""

    last_modified_at: datetime
    last_modified_by: PersonLastEditorSchema | None = None


class PersonAdminListResponseSchema(BaseModel):
    """Protected paginated list used by the editorial panel."""

    items: list[PersonAdminListItemSchema]
    total: int
    page: int
    per_page: int
    pages: int


class PersonVersionSchema(BaseModel):
    """Version record schema."""

    id: uuid.UUID
    person_id: uuid.UUID
    version_number: int
    snapshot: dict[str, Any]
    changed_by_id: uuid.UUID | None = None
    changed_at: datetime | None = None
    change_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)
