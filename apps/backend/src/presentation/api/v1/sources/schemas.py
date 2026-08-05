"""
Pydantic v2 schemas for Sources & Media (Bibliography, HistoricalSource, Image, Document).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from src.domain.sources.models import DocumentType, ImageLicense, SourceType


# ==============================================================================
# BIBLIOGRAPHY SCHEMAS
# ==============================================================================


class BibliographyCreateSchema(BaseModel):
    source_type: SourceType = Field(default=SourceType.BOOK)
    title: str = Field(..., min_length=2, max_length=1000)
    subtitle: str | None = Field(None, max_length=500)
    authors: str | None = Field(None, max_length=1000)
    editor: str | None = Field(None, max_length=500)
    publisher: str | None = Field(None, max_length=500)
    place_of_publication: str | None = Field(None, max_length=300)
    year: int | None = None
    edition: str | None = Field(None, max_length=100)
    volume: str | None = Field(None, max_length=100)
    pages: str | None = Field(None, max_length=100)
    isbn: str | None = Field(None, max_length=20)
    issn: str | None = Field(None, max_length=20)
    doi: str | None = Field(None, max_length=500)
    url: str | None = Field(None, max_length=2000)
    language: str | None = Field(None, max_length=10)
    abstract: str | None = None
    reliability_score: int | None = Field(None, ge=1, le=5)
    notes: str | None = None


class BibliographyUpdateSchema(BaseModel):
    source_type: SourceType | None = None
    title: str | None = Field(None, min_length=2, max_length=1000)
    subtitle: str | None = None
    authors: str | None = None
    editor: str | None = None
    publisher: str | None = None
    place_of_publication: str | None = None
    year: int | None = None
    edition: str | None = None
    volume: str | None = None
    pages: str | None = None
    isbn: str | None = None
    issn: str | None = None
    doi: str | None = None
    url: str | None = None
    language: str | None = None
    abstract: str | None = None
    reliability_score: int | None = Field(None, ge=1, le=5)
    notes: str | None = None


class BibliographySchema(BibliographyCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# HISTORICAL SOURCE SCHEMAS
# ==============================================================================


class HistoricalSourceCreateSchema(BaseModel):
    title: str = Field(..., min_length=2, max_length=1000)
    original_title: str | None = Field(None, max_length=1000)
    source_type: SourceType = Field(default=SourceType.MANUSCRIPT)
    repository: str | None = Field(None, max_length=500)
    call_number: str | None = Field(None, max_length=200)
    date_range: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=100)
    description: str | None = None
    digitization_url: str | None = Field(None, max_length=2000)
    is_digitized: bool = False


class HistoricalSourceUpdateSchema(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=1000)
    original_title: str | None = None
    source_type: SourceType | None = None
    repository: str | None = None
    call_number: str | None = None
    date_range: str | None = None
    language: str | None = None
    description: str | None = None
    digitization_url: str | None = None
    is_digitized: bool | None = None


class HistoricalSourceSchema(HistoricalSourceCreateSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# IMAGE SCHEMAS
# ==============================================================================


class ImageCreateSchema(BaseModel):
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


# ==============================================================================
# DOCUMENT SCHEMAS
# ==============================================================================


class DocumentCreateSchema(BaseModel):
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
