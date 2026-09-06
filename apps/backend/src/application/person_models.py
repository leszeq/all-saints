"""Application result models shared by person-facing use cases."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.domain.sources.models import ImageLicense


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


class PersonLastEditorSchema(BaseModel):
    """Minimal editor identity exposed only by the protected admin list."""

    id: uuid.UUID
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonLocalizedSummarySchema(BaseModel):
    """Language resolution metadata and lightweight catalogue content."""

    requested_locale: str
    resolved_locale: str
    fallback_used: bool
    source: Literal["translation", "legacy_person_columns"]
    canonical_name: str | None = None
    summary: str | None = None


class PersonLocalizedContentSchema(PersonLocalizedSummarySchema):
    """One language-coherent view of detailed editorial person content."""

    biography: str | None = None
    prayers: str | None = None
    iconographic_attributes: str | None = None
