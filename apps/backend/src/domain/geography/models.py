"""
Geography domain models.

Covers: Country, Region, Diocese, Place, ReligiousOrder,
        Church, PilgrimageSite, Sanctuary, Shrine.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.base import Base, BaseModel

if TYPE_CHECKING:
    from src.domain.hagiography.models import Person


# ==============================================================================
# ENUMS
# ==============================================================================


class ChurchType(StrEnum):
    """Type of sacred building."""

    PARISH = "parish"
    CATHEDRAL = "cathedral"
    BASILICA = "basilica"
    CHAPEL = "chapel"
    MONASTERY = "monastery"
    SANCTUARY = "sanctuary"
    SHRINE = "shrine"
    PILGIMAGE_SITE = "pilgrimage_site"
    OTHER = "other"


class OrderCharism(StrEnum):
    """Religious order charism/spirituality."""

    CONTEMPLATIVE = "contemplative"
    APOSTOLIC = "apostolic"
    MENDICANT = "mendicant"
    MONASTIC = "monastic"
    MISSIONARY = "missionary"
    EDUCATIONAL = "educational"
    CHARITABLE = "charitable"
    MILITARY = "military"
    OTHER = "other"


# ==============================================================================
# COUNTRY
# ==============================================================================


class Country(BaseModel, Base):
    """A sovereign state or territory."""

    __tablename__ = "countries"
    __table_args__ = (
        UniqueConstraint("iso_code_alpha2", name="uq_country_iso2"),
        UniqueConstraint("iso_code_alpha3", name="uq_country_iso3"),
        Index("ix_countries_name_pl", "name_pl"),
        {"comment": "Countries and territories"},
    )

    # Names in multiple languages
    name_pl: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_la: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Latin name"
    )
    name_local: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Name in the country's local language"
    )

    # Codes
    iso_code_alpha2: Mapped[str | None] = mapped_column(
        String(2), nullable=True, comment="ISO 3166-1 alpha-2 (e.g. PL)"
    )
    iso_code_alpha3: Mapped[str | None] = mapped_column(
        String(3), nullable=True, comment="ISO 3166-1 alpha-3 (e.g. POL)"
    )
    continent: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Geography
    capital: Mapped[str | None] = mapped_column(String(200), nullable=True)
    flag_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Historical
    is_historical: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for no-longer-existing states (e.g. Byzantine Empire)",
    )
    historical_period: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    regions: Mapped[list["Region"]] = relationship("Region", back_populates="country")
    places: Mapped[list["Place"]] = relationship("Place", back_populates="country")
    dioceses: Mapped[list["Diocese"]] = relationship(
        "Diocese", back_populates="country"
    )


# ==============================================================================
# REGION
# ==============================================================================


class Region(BaseModel, Base):
    """Administrative region within a country."""

    __tablename__ = "regions"
    __table_args__ = (
        Index("ix_regions_country_id", "country_id"),
        {"comment": "Administrative regions / provinces"},
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    name_local: Mapped[str | None] = mapped_column(String(300), nullable=True)
    country_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    country: Mapped["Country"] = relationship("Country", back_populates="regions")
    places: Mapped[list["Place"]] = relationship("Place", back_populates="region")


# ==============================================================================
# DIOCESE
# ==============================================================================


class Diocese(BaseModel, Base):
    """Catholic diocese or archdiocese."""

    __tablename__ = "dioceses"
    __table_args__ = (
        Index("ix_dioceses_country_id", "country_id"),
        {"comment": "Catholic dioceses and archdioceses"},
    )

    name: Mapped[str] = mapped_column(String(400), nullable=False)
    name_la: Mapped[str | None] = mapped_column(String(400), nullable=True)
    is_archdiocese: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suppressed_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    country: Mapped["Country | None"] = relationship(
        "Country", back_populates="dioceses"
    )
    places: Mapped[list["Place"]] = relationship("Place", back_populates="diocese")
    churches: Mapped[list["Church"]] = relationship(
        "Church", back_populates="diocese"
    )


# ==============================================================================
# PLACE
# ==============================================================================


class Place(BaseModel, Base):
    """
    A specific geographic location (city, village, monastery, etc.).

    Includes coordinates for map rendering.
    """

    __tablename__ = "places"
    __table_args__ = (
        Index("ix_places_country_id", "country_id"),
        Index("ix_places_name", "name"),
        {"comment": "Geographic locations"},
    )

    name: Mapped[str] = mapped_column(String(400), nullable=False)
    name_la: Mapped[str | None] = mapped_column(String(400), nullable=True)
    name_local: Mapped[str | None] = mapped_column(String(400), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location hierarchy
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
    )
    diocese_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dioceses.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Coordinates
    latitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7), nullable=True, comment="WGS84 latitude"
    )
    longitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7), nullable=True, comment="WGS84 longitude"
    )

    # Relationships
    country: Mapped["Country | None"] = relationship("Country", back_populates="places")
    region: Mapped["Region | None"] = relationship("Region", back_populates="places")
    diocese: Mapped["Diocese | None"] = relationship("Diocese", back_populates="places")
    churches: Mapped[list["Church"]] = relationship("Church", back_populates="place")


# ==============================================================================
# RELIGIOUS ORDER
# ==============================================================================


class ReligiousOrder(BaseModel, Base):
    """
    Catholic religious order, congregation, or institute.

    Examples: Dominicans, Franciscans, Jesuits, Benedictines.
    """

    __tablename__ = "religious_orders"
    __table_args__ = (
        Index("ix_religious_orders_abbreviation", "abbreviation"),
        {"comment": "Catholic religious orders and congregations"},
    )

    # Names
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_la: Mapped[str | None] = mapped_column(String(500), nullable=True)
    name_local: Mapped[str | None] = mapped_column(String(500), nullable=True)
    abbreviation: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True
    )

    # Founding
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    founded_place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    founder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="FK to persons.id – set after person is created",
    )
    suppressed_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Charism & description
    charism: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="OrderCharism enum value"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Papally approved
    papal_approval_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_suppressed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships
    founded_place: Mapped["Place | None"] = relationship("Place")


# ==============================================================================
# CHURCH / SACRED BUILDING
# ==============================================================================


class Church(BaseModel, Base):
    """
    A Catholic church, basilica, chapel, sanctuary or shrine.

    May serve as a pilgrimage site or house relics of a saint.
    """

    __tablename__ = "churches"
    __table_args__ = (
        Index("ix_churches_place_id", "place_id"),
        Index("ix_churches_type", "church_type"),
        {"comment": "Catholic churches, basilicas, sanctuaries, shrines"},
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_la: Mapped[str | None] = mapped_column(String(500), nullable=True)
    church_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ChurchType.PARISH,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    diocese_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dioceses.id", ondelete="SET NULL"),
        nullable=True,
    )
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # Building info
    construction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consecration_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Flags
    is_pilgrimage_site: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_national_sanctuary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Relationships
    place: Mapped["Place | None"] = relationship("Place", back_populates="churches")
    diocese: Mapped["Diocese | None"] = relationship(
        "Diocese", back_populates="churches"
    )
