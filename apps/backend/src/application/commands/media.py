"""Validated application inputs for image and document metadata."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from src.domain.sources.models import DocumentType, ImageLicense


class CreateImageCommand(BaseModel):
    """Create metadata for an image, optionally attached to a person."""

    person_id: uuid.UUID | None = None
    url: str = Field(..., min_length=5, max_length=2000)
    thumbnail_url: str | None = Field(None, max_length=2000)
    storage_key: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    image_type: str | None = Field(None, max_length=50)
    license: ImageLicense = Field(default=ImageLicense.UNKNOWN)
    photographer: str | None = Field(None, max_length=300)
    source_url: str | None = Field(None, max_length=2000)
    year_created: int | None = None
    is_primary: bool = False
    sort_order: int = 0
    width_px: int | None = None
    height_px: int | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = Field(None, max_length=100)


class CreateDocumentCommand(BaseModel):
    """Create metadata for an editorial document."""

    person_id: uuid.UUID | None = None
    title: str = Field(..., min_length=2, max_length=500)
    document_type: DocumentType = Field(default=DocumentType.OTHER)
    language_code: str | None = Field(None, max_length=10)
    description: str | None = None
    file_url: str | None = Field(None, max_length=2000)
    storage_key: str | None = Field(None, max_length=500)
    file_size_bytes: int | None = None
    mime_type: str | None = Field(None, max_length=100)
    is_public: bool = True
