"""
Sources domain models.

Covers: Bibliography, HistoricalSource, PersonSource,
        Image, Document, ExternalLink.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.base import Base, BaseModel


# ==============================================================================
# ENUMS
# ==============================================================================


class SourceType(StrEnum):
    """Type of bibliographic source."""

    BOOK = "book"
    ARTICLE = "article"
    ENCYCLOPEDIA = "encyclopedia"
    WEBSITE = "website"
    MANUSCRIPT = "manuscript"
    ARCHIVE = "archive"
    DOCUMENT = "document"
    HAGIOGRAPHY = "hagiography"
    VITA = "vita"
    OTHER = "other"


class ImageLicense(StrEnum):
    """Image license type."""

    PUBLIC_DOMAIN = "public_domain"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    CC_BY_NC = "cc_by_nc"
    CC_BY_NC_SA = "cc_by_nc_sa"
    ALL_RIGHTS_RESERVED = "all_rights_reserved"
    FAIR_USE = "fair_use"
    UNKNOWN = "unknown"


class DocumentType(StrEnum):
    """Type of associated document."""

    DECREE = "decree"
    BULL = "bull"
    ENCYCLICAL = "encyclical"
    BIOGRAPHY = "biography"
    LETTER = "letter"
    VITA = "vita"
    PROCESS = "process"       # Causa documentation
    OTHER = "other"


# ==============================================================================
# BIBLIOGRAPHY
# ==============================================================================


class Bibliography(BaseModel, Base):
    """
    A bibliographic source (book, article, website, manuscript).

    Used as a reference for person data, miracles, and other content.
    """

    __tablename__ = "bibliography"
    __table_args__ = (
        Index("ix_bibliography_source_type", "source_type"),
        Index("ix_bibliography_year", "year"),
        {"comment": "Bibliographic sources and references"},
    )

    # Identification
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SourceType.BOOK
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Authors & publication
    authors: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="Author(s) in citation format"
    )
    editor: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(500), nullable=True)
    place_of_publication: Mapped[str | None] = mapped_column(String(300), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Identifiers
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    issn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    url_access_date: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Language & scope
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Evaluation
    reliability_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Editorial reliability score 1-5",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    person_sources: Mapped[list["PersonSource"]] = relationship(
        "PersonSource", back_populates="bibliography"
    )


# ==============================================================================
# HISTORICAL SOURCE
# ==============================================================================


class HistoricalSource(BaseModel, Base):
    """
    Primary historical source (manuscript, archive, inscription).

    Distinct from Bibliography (secondary sources).
    """

    __tablename__ = "historical_sources"
    __table_args__ = (
        Index("ix_historical_sources_repository", "repository"),
        {"comment": "Primary historical sources"},
    )

    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SourceType.MANUSCRIPT
    )
    repository: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Archive or library holding the source"
    )
    call_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_range: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Date range of the source (e.g. 1235-1240)"
    )
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    digitization_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_digitized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# ==============================================================================
# PERSON SOURCE (association)
# ==============================================================================


class PersonSource(BaseModel, Base):
    """Association linking a Person to a Bibliography or HistoricalSource."""

    __tablename__ = "person_sources"
    __table_args__ = (
        Index("ix_person_sources_person_id", "person_id"),
        Index("ix_person_sources_bibliography_id", "bibliography_id"),
        {"comment": "Source references for persons"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    bibliography_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bibliography.id", ondelete="SET NULL"),
        nullable=True,
    )
    historical_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("historical_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Relevance 1-5"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Primary source for this person"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    bibliography: Mapped["Bibliography | None"] = relationship(
        "Bibliography", back_populates="person_sources"
    )


# ==============================================================================
# IMAGE
# ==============================================================================


class Image(BaseModel, Base):
    """
    An image associated with a person or other entity.

    Includes metadata for proper attribution and licensing.
    """

    __tablename__ = "images"
    __table_args__ = (
        Index("ix_images_person_id", "person_id"),
        Index("ix_images_is_primary", "is_primary"),
        {"comment": "Images associated with persons and entities"},
    )

    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Storage
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="MinIO/S3 object key"
    )

    # Metadata
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="portrait/icon/fresco/sculpture/relic/document/other",
    )
    license: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ImageLicense.UNKNOWN
    )
    photographer: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    year_created: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Display
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Technical
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


# ==============================================================================
# DOCUMENT
# ==============================================================================


class Document(BaseModel, Base):
    """
    An official church document or file associated with a person or causa.

    Examples: papal bulls, decrees, canonization process documents.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_person_id", "person_id"),
        {"comment": "Church documents and files"},
    )

    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=DocumentType.OTHER
    )
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
