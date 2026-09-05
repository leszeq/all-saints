"""Application result models shared by person-facing use cases."""

from __future__ import annotations

import uuid

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
