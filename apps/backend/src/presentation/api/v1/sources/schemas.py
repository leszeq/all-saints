"""
Pydantic v2 schemas for Sources & Media (Bibliography, HistoricalSource, Image, Document).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.media import CreateDocumentCommand, CreateImageCommand
from src.application.commands.person_sources import (
    CreatePersonSourceCommand,
    CreatePersonWebSourceCommand,
)
from src.application.commands.source_catalogue import (
    CreateBibliographyCommand,
    CreateHistoricalSourceCommand,
    UpdateBibliographyCommand,
    UpdateHistoricalSourceCommand,
)
from src.domain.sources.models import DocumentType, ImageLicense

# ==============================================================================
# BIBLIOGRAPHY SCHEMAS
# ==============================================================================


class BibliographyCreateSchema(CreateBibliographyCommand):
    """HTTP input for bibliography creation."""


class BibliographyUpdateSchema(UpdateBibliographyCommand):
    """HTTP input for bibliography updates."""


class BibliographySchema(BibliographyCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# HISTORICAL SOURCE SCHEMAS
# ==============================================================================


class HistoricalSourceCreateSchema(CreateHistoricalSourceCommand):
    """HTTP input for historical-source creation."""


class HistoricalSourceUpdateSchema(UpdateHistoricalSourceCommand):
    """HTTP input for historical-source updates."""


class HistoricalSourceSchema(HistoricalSourceCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# PERSON SOURCE LINKS
# ==============================================================================


class PersonSourceCreateSchema(CreatePersonSourceCommand):
    """Attach exactly one bibliographic or historical source to a person."""


class PersonWebSourceCreateSchema(CreatePersonWebSourceCommand):
    """Create a website bibliography entry and attach it to a person atomically."""


class PersonSourceSchema(PersonSourceCreateSchema):
    """A source assignment enriched with the selected source metadata."""

    id: uuid.UUID
    person_id: uuid.UUID
    bibliography: BibliographySchema | None = None
    historical_source: HistoricalSourceSchema | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# IMAGE SCHEMAS
# ==============================================================================


class ImageCreateSchema(CreateImageCommand):
    """HTTP input for image metadata creation."""


class ImageUpdateSchema(BaseModel):
    url: str | None = Field(None, min_length=5, max_length=2000)
    thumbnail_url: str | None = None
    title: str | None = None
    description: str | None = None
    license: ImageLicense | None = None
    photographer: str | None = None
    is_primary: bool | None = None
    sort_order: int | None = None


class ImageSchema(ImageCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageUploadSchema(BaseModel):
    """Metadata returned after a validated image file upload."""

    url: str
    thumbnail_url: str
    storage_key: str
    width_px: int
    height_px: int
    file_size_bytes: int
    mime_type: str = "image/webp"


class SourceStatsSchema(BaseModel):
    """Public source statistics displayed in the reader-facing portal."""

    bibliography_sources: int
    historical_sources: int
    person_source_links: int
    documented_persons: int
    total_published_persons: int
    images: int
    unknown_license_images: int

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# DOCUMENT SCHEMAS
# ==============================================================================


class DocumentCreateSchema(CreateDocumentCommand):
    """HTTP input for document metadata creation."""


class DocumentUpdateSchema(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=500)
    document_type: DocumentType | None = None
    language_code: str | None = None
    description: str | None = None
    file_url: str | None = None
    is_public: bool | None = None


class DocumentSchema(DocumentCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
