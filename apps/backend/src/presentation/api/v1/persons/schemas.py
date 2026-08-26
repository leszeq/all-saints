"""
Pydantic v2 schemas for Person (Saints, Blessed, etc.) API.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.hagiography.models import (
    Era,
    Gender,
    LiturgicalColor,
    PersonType,
    PublicationStatus,
)
from src.domain.sources.models import ImageLicense

OPTIONAL_UUID_FIELDS = (
    "birth_place_id",
    "death_place_id",
    "birth_country_id",
    "death_country_id",
    "nationality_id",
    "state_of_life_id",
)


def _blank_as_none(value: object) -> object:
    """Treat blank HTML form values as an omitted optional field."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


# ==============================================================================
# BASE & CREATE/UPDATE SCHEMAS
# ==============================================================================


def _validate_avatar_url(value: object) -> str | None:
    """Allow HTTP(S) and application-relative media URLs only."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Adres obrazu musi być tekstem")
    normalized = value.strip()
    if not normalized:
        return None
    if not normalized.startswith(("https://", "http://", "/")):
        raise ValueError("Adres obrazu musi używać HTTP(S) lub ścieżki względnej")
    return normalized


class PersonAvatarInputSchema(BaseModel):
    """Editable primary portrait metadata stored in the media catalogue."""

    url: str = Field(..., min_length=5, max_length=2000)
    thumbnail_url: str | None = Field(None, max_length=2000)
    title: str | None = Field(None, max_length=500)
    license: ImageLicense = Field(default=ImageLicense.UNKNOWN)
    photographer: str | None = Field(None, max_length=300)
    source_url: str | None = Field(None, max_length=2000)
    storage_key: str | None = Field(None, max_length=500)
    width_px: int | None = Field(None, gt=0)
    height_px: int | None = Field(None, gt=0)
    file_size_bytes: int | None = Field(None, ge=0)
    mime_type: str | None = Field(None, max_length=100)

    @field_validator("url", "thumbnail_url", "source_url", mode="before")
    @classmethod
    def validate_urls(cls, value: object) -> str | None:
        return _validate_avatar_url(value)


class PersonPatronageInputSchema(BaseModel):
    """Editable patronage attached to a person record."""

    patronage_type: str = Field(..., min_length=2, max_length=50)
    name_pl: str = Field(..., min_length=2, max_length=500)
    name_en: str | None = Field(None, max_length=500)
    description: str | None = None
    is_official: bool = False


class PersonBeatificationInputSchema(BaseModel):
    """Editable beatification facts; partial dates may use the year only."""

    beatification_date: str | None = Field(None, max_length=50)
    beatification_year: int | None = Field(None, ge=1, le=2100)

    @field_validator("beatification_date", mode="before")
    @classmethod
    def normalize_date(cls, value: object) -> object:
        return _blank_as_none(value)


class PersonCanonizationInputSchema(BaseModel):
    """Editable canonization facts; partial dates may use the year only."""

    canonization_date: str | None = Field(None, max_length=50)
    canonization_year: int | None = Field(None, ge=1, le=2100)

    @field_validator("canonization_date", mode="before")
    @classmethod
    def normalize_date(cls, value: object) -> object:
        return _blank_as_none(value)


class PersonBaseSchema(BaseModel):
    """Base fields for Person payload."""

    person_type: PersonType = Field(default=PersonType.SAINT, description="saint, blessed, venerable, servant_of_god, candidate")
    canonical_name: str = Field(..., min_length=2, max_length=500, description="Full canonical display name (e.g. Św. Franciszek z Asyżu)")
    canonical_name_en: str | None = Field(None, max_length=500)
    latin_name: str | None = Field(None, max_length=500)
    original_name: str | None = Field(None, max_length=500)
    surnames: str | None = Field(None, max_length=500)
    religious_name: str | None = Field(None, max_length=300)
    epithets: list[str] | None = Field(default=None, description="Nicknames or epithets e.g. ['z Asyżu', 'Wielki']")

    gender: Gender = Field(default=Gender.UNKNOWN)
    era: Era | None = Field(None)
    century: int | None = Field(None, ge=-50, le=22)

    birth_date: str | None = Field(None, max_length=50, description="e.g. '1181' or 'ca. 1181'")
    birth_year: int | None = Field(None, ge=-5000, le=2100)
    death_date: str | None = Field(None, max_length=50)
    death_year: int | None = Field(None, ge=-5000, le=2100)

    birth_place_id: uuid.UUID | None = None
    death_place_id: uuid.UUID | None = None
    birth_country_id: uuid.UUID | None = None
    death_country_id: uuid.UUID | None = None
    nationality_id: uuid.UUID | None = None
    state_of_life_id: uuid.UUID | None = None

    summary_pl: str | None = Field(None, description="Short summary biography in Polish")
    biography_pl: str | None = Field(None, description="Full detailed biography in Polish")
    summary_en: str | None = None
    biography_en: str | None = None

    iconographic_attributes: str | None = None
    prayers: str | None = None
    works: str | None = None

    liturgical_color: LiturgicalColor | None = None
    is_featured: bool = False
    external_ids: dict[str, Any] | None = None
    avatar: PersonAvatarInputSchema | None = None
    patronages: list[PersonPatronageInputSchema] = Field(default_factory=list)
    beatification: PersonBeatificationInputSchema | None = None
    canonization: PersonCanonizationInputSchema | None = None

    @field_validator(*OPTIONAL_UUID_FIELDS, "era", "liturgical_color", mode="before")
    @classmethod
    def normalize_optional_selects(cls, value: object) -> object:
        """Accept the empty value emitted by native HTML select controls."""
        return _blank_as_none(value)


class PersonCreateSchema(PersonBaseSchema):
    """Payload for creating a new Person."""

    status: PublicationStatus = Field(default=PublicationStatus.DRAFT)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "canonical_name": "Św. Jan Paweł II",
                    "canonical_name_en": "St. John Paul II",
                    "person_type": "saint",
                    "status": "draft",
                    "gender": "male",
                    "era": "modern",
                    "birth_year": 1920,
                    "death_year": 2005,
                    "birth_country_id": None,
                    "death_country_id": None,
                    "state_of_life_id": None,
                    "summary_pl": "Papież Kościoła katolickiego w latach 1978–2005.",
                    "biography_pl": "Biogram przygotowany przez redakcję.",
                    "is_featured": False,
                }
            ]
        }
    )


class PersonUpdateSchema(BaseModel):
    """Payload for updating a Person (all fields optional)."""

    person_type: PersonType | None = None
    status: PublicationStatus | None = None
    canonical_name: str | None = Field(None, min_length=2, max_length=500)
    canonical_name_en: str | None = None
    latin_name: str | None = None
    original_name: str | None = None
    surnames: str | None = None
    religious_name: str | None = None
    epithets: list[str] | None = None

    gender: Gender | None = None
    era: Era | None = None
    century: int | None = None

    birth_date: str | None = None
    birth_year: int | None = None
    death_date: str | None = None
    death_year: int | None = None

    birth_place_id: uuid.UUID | None = None
    death_place_id: uuid.UUID | None = None
    birth_country_id: uuid.UUID | None = None
    death_country_id: uuid.UUID | None = None
    nationality_id: uuid.UUID | None = None
    state_of_life_id: uuid.UUID | None = None

    summary_pl: str | None = None
    biography_pl: str | None = None
    summary_en: str | None = None
    biography_en: str | None = None

    iconographic_attributes: str | None = None
    prayers: str | None = None
    works: str | None = None

    liturgical_color: LiturgicalColor | None = None
    is_featured: bool | None = None
    external_ids: dict[str, Any] | None = None
    avatar: PersonAvatarInputSchema | None = None
    patronages: list[PersonPatronageInputSchema] | None = None
    beatification: PersonBeatificationInputSchema | None = None
    canonization: PersonCanonizationInputSchema | None = None
    change_summary: str | None = Field(None, description="Optional description of changes for version log")

    @field_validator(*OPTIONAL_UUID_FIELDS, "era", "liturgical_color", mode="before")
    @classmethod
    def normalize_optional_selects(cls, value: object) -> object:
        """Accept the empty value emitted by native HTML select controls."""
        return _blank_as_none(value)


# ==============================================================================
# RESPONSE SCHEMAS
# ==============================================================================


class PersonAvatarSchema(BaseModel):
    """Primary portrait returned with person list and detail responses."""

    id: uuid.UUID
    url: str
    thumbnail_url: str | None = None
    title: str | None = None
    license: ImageLicense
    photographer: str | None = None
    source_url: str | None = None

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
    liturgical_color: LiturgicalColor | None = None
    is_featured: bool
    avatar: PersonAvatarSchema | None = None
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


class PersonPatronageSchema(BaseModel):
    """Patronage returned on the public person profile."""

    id: uuid.UUID
    patronage_type: str
    name_pl: str
    name_en: str | None = None
    description: str | None = None
    is_official: bool

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
    patronages: list[PersonPatronageSchema] = Field(default_factory=list)
    orders: list[PersonOrderMembershipSchema] = Field(default_factory=list)
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


class PersonLastEditorSchema(BaseModel):
    """Minimal editor identity exposed only by the protected admin list."""

    id: uuid.UUID
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


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
    changed_at: str | None = None
    change_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)
