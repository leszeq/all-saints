"""
Hagiography domain models – the core of the system.

Covers: Person (Saint/Blessed/ServantOfGod/Venerable/Candidate),
        Canonization, Beatification, Miracle, Patronage,
        PersonVersion (audit snapshots), PersonRelationship,
        Pope (as a special person subtype).
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column, relationship

from src.domain.base import Base, BaseModel

if TYPE_CHECKING:
    from src.domain.geography.models import Country, Place, ReligiousOrder
    from src.domain.identity.models import User
    from src.domain.sources.models import Image, Bibliography
    from src.domain.liturgy.models import Feast


# ==============================================================================
# ENUMS
# ==============================================================================


class PersonType(StrEnum):
    """Canonical status in the Church's hagiographic catalogue."""

    SAINT = "saint"                         # Kanonizowany
    BLESSED = "blessed"                     # Błogosławiony
    VENERABLE = "venerable"                 # Czcigodny
    SERVANT_OF_GOD = "servant_of_god"       # Sługa Boży
    CANDIDATE = "candidate"                 # Kandydat (causa otwarta)


class Gender(StrEnum):
    """Biological sex of the person."""

    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class PublicationStatus(StrEnum):
    """Content lifecycle state."""

    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LiturgicalColor(StrEnum):
    """Liturgical colour for the feast day."""

    WHITE = "white"       # Biały
    RED = "red"           # Czerwony
    GREEN = "green"       # Zielony
    VIOLET = "violet"     # Fioletowy
    ROSE = "rose"         # Różowy
    BLACK = "black"       # Czarny (rare)
    GOLD = "gold"         # Złoty


class Era(StrEnum):
    """Historical epoch."""

    APOSTOLIC = "apostolic"           # I w.
    EARLY_CHURCH = "early_church"     # II–V w.
    LATE_ANTIQUITY = "late_antiquity" # V–VII w.
    MEDIEVAL = "medieval"             # VIII–XV w.
    EARLY_MODERN = "early_modern"     # XVI–XVIII w.
    MODERN = "modern"                 # XIX–XX w.
    CONTEMPORARY = "contemporary"     # XXI w.
    UNKNOWN = "unknown"


class MiracleStatus(StrEnum):
    """Vatican recognition status of a miracle."""

    REPORTED = "reported"
    UNDER_INVESTIGATION = "under_investigation"
    APPROVED = "approved"
    REJECTED = "rejected"


class RelationshipType(StrEnum):
    """Type of relationship between two persons."""

    SPIRITUAL_DIRECTOR = "spiritual_director"
    DISCIPLE = "disciple"
    FELLOW_RELIGIOUS = "fellow_religious"
    CONTEMPORARY = "contemporary"
    MARTYR_COMPANION = "martyr_companion"
    FAMILY = "family"
    FRIEND = "friend"
    MENTOR = "mentor"
    STUDENT = "student"
    OTHER = "other"


# ==============================================================================
# STATE OF LIFE
# ==============================================================================


class StateOfLife(BaseModel, Base):
    """State of life of the person (priest, bishop, layperson, etc.)."""

    __tablename__ = "states_of_life"

    name_pl: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_la: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ==============================================================================
# OCCUPATION
# ==============================================================================


class Occupation(BaseModel, Base):
    """Occupation or vocation of a person (e.g. priest, doctor, queen)."""

    __tablename__ = "occupations"

    name_pl: Mapped[str] = mapped_column(String(300), nullable=False)
    name_en: Mapped[str] = mapped_column(String(300), nullable=False)
    name_la: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ==============================================================================
# CATEGORY & TAG
# ==============================================================================


class Category(BaseModel, Base):
    """Hierarchical content category (e.g. Martyrs > Early Church Martyrs)."""

    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_parent_id", "parent_id"),
        {"comment": "Hierarchical content categories"},
    )

    name_pl: Mapped[str] = mapped_column(String(300), nullable=False)
    name_en: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    parent: Mapped["Category | None"] = relationship(
        "Category", remote_side="Category.id", back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent"
    )


class Tag(BaseModel, Base):
    """Flat content tag for flexible cross-cutting classification."""

    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_tag_slug"),
        {"comment": "Flat content tags"},
    )

    name_pl: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    color: Mapped[str | None] = mapped_column(
        String(7), nullable=True, comment="Hex color for UI display"
    )


# ==============================================================================
# PERSON (core entity)
# ==============================================================================


class Person(BaseModel, Base):
    """
    Central entity representing any person in the hagiographic catalogue.

    A Person can be a saint, blessed, venerable, servant of God, or candidate.
    The ``person_type`` field determines the canonical status.

    Full-text search is supported via the ``search_vector`` tsvector column,
    which is maintained by a PostgreSQL trigger.
    """

    __tablename__ = "persons"
    __table_args__ = (
        Index("ix_persons_person_type", "person_type"),
        Index("ix_persons_gender", "gender"),
        Index("ix_persons_era", "era"),
        Index("ix_persons_birth_country_id", "birth_country_id"),
        Index("ix_persons_death_country_id", "death_country_id"),
        Index("ix_persons_status", "status"),
        Index(
            "ix_persons_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        {"comment": "All persons in the hagiographic catalogue"},
    )

    # ── Identity ───────────────────────────────────────────────────────────────
    person_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=PersonType.SAINT,
        comment="PersonType enum: saint/blessed/venerable/servant_of_god/candidate",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PublicationStatus.DRAFT,
        comment="Publication status",
    )

    # ── Names ──────────────────────────────────────────────────────────────────
    canonical_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="Main display name (Polish)",
    )
    canonical_name_en: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Main display name (English)"
    )
    latin_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Name in Latin"
    )
    original_name: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Name in the original language"
    )
    surnames: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Family name(s)"
    )
    religious_name: Mapped[str | None] = mapped_column(
        String(300), nullable=True, comment="Name taken in religious life"
    )
    epithets: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment='Epithets/nicknames (e.g. ["of Assisi", "the Great"])'
    )
    slug: Mapped[str] = mapped_column(
        String(600),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe unique identifier",
    )

    # ── Demographics ───────────────────────────────────────────────────────────
    gender: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default=Gender.UNKNOWN,
    )
    era: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="Historical epoch"
    )
    century: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Century (positive = AD, negative = BC)",
    )

    # ── Dates & Years ──────────────────────────────────────────────────────────
    birth_date: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Exact or approximate birth date as string (e.g. 'ca. 1181')",
    )
    birth_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Numeric birth year for filtering"
    )
    death_date: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Exact or approximate death date"
    )
    death_year: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Numeric death year for filtering"
    )

    # ── Geography ──────────────────────────────────────────────────────────────
    birth_place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    death_place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    birth_country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    death_country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    nationality_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    state_of_life_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("states_of_life.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Hagiographic content ───────────────────────────────────────────────────
    summary_pl: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Short biography (Polish, max 500 chars)"
    )
    biography_pl: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Full biography in Polish"
    )
    summary_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    biography_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    iconographic_attributes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Iconographic symbols and attributes"
    )
    prayers: Mapped[str | None] = mapped_column(Text, nullable=True)
    works: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Literary or artistic works"
    )

    # ── Liturgy ────────────────────────────────────────────────────────────────
    liturgical_color: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="LiturgicalColor enum – color of vestments on feast day",
    )

    # ── Full-text search ───────────────────────────────────────────────────────
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
        comment="PostgreSQL tsvector – maintained by trigger",
    )

    # ── AI ─────────────────────────────────────────────────────────────────────
    embedding_vector: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Semantic embedding vector (stored as JSON array for portability)",
    )
    ai_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated biography summary",
    )
    ai_tags: Mapped[list | None] = mapped_column(
        JSONB, nullable=True, comment="AI-generated tags"
    )

    # ── Metadata ───────────────────────────────────────────────────────────────
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_name: Mapped[str | None] = mapped_column(
        String(600),
        nullable=True,
        index=True,
        comment="Normalised name for alphabetical sorting (no diacritics)",
    )
    external_ids: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='External system IDs (e.g. {"wikidata": "Q123", "vatican": "P456"})',
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    birth_place: Mapped["Place | None"] = relationship(
        "Place", foreign_keys=[birth_place_id]
    )
    death_place: Mapped["Place | None"] = relationship(
        "Place", foreign_keys=[death_place_id]
    )
    birth_country: Mapped["Country | None"] = relationship(
        "Country", foreign_keys=[birth_country_id]
    )
    nationality: Mapped["Country | None"] = relationship(
        "Country", foreign_keys=[nationality_id]
    )
    state_of_life: Mapped["StateOfLife | None"] = relationship("StateOfLife")

    canonization: Mapped["Canonization | None"] = relationship(
        "Canonization", back_populates="person", uselist=False
    )
    beatification: Mapped["Beatification | None"] = relationship(
        "Beatification", back_populates="person", uselist=False
    )
    miracles: Mapped[list["Miracle"]] = relationship(
        "Miracle", back_populates="person"
    )
    patronages: Mapped[list["Patronage"]] = relationship(
        "Patronage", back_populates="person"
    )
    translations: Mapped[list["PersonTranslation"]] = relationship(
        "PersonTranslation", back_populates="person", cascade="all, delete-orphan"
    )
    versions: Mapped[list["PersonVersion"]] = relationship(
        "PersonVersion", back_populates="person", order_by="PersonVersion.version_number"
    )
    occupations: Mapped[list["PersonOccupation"]] = relationship(
        "PersonOccupation", back_populates="person"
    )
    orders: Mapped[list["PersonOrder"]] = relationship(
        "PersonOrder", back_populates="person"
    )
    categories: Mapped[list["PersonCategory"]] = relationship(
        "PersonCategory", back_populates="person"
    )
    tags: Mapped[list["PersonTag"]] = relationship("PersonTag", back_populates="person")

    # Relationships between persons
    relationships_as_a: Mapped[list["PersonRelationship"]] = relationship(
        "PersonRelationship",
        foreign_keys="PersonRelationship.person_a_id",
        back_populates="person_a",
    )
    relationships_as_b: Mapped[list["PersonRelationship"]] = relationship(
        "PersonRelationship",
        foreign_keys="PersonRelationship.person_b_id",
        back_populates="person_b",
    )

    @property
    def all_relationships(self) -> list["PersonRelationship"]:
        """All relationships regardless of direction."""
        return self.relationships_as_a + self.relationships_as_b


# ==============================================================================
# PERSON TRANSLATION
# ==============================================================================


class PersonTranslation(BaseModel, Base):
    """Multilingual content for a Person record."""

    __tablename__ = "person_translations"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "language_code", name="uq_person_translation_lang"
        ),
        Index("ix_person_translations_person_id", "person_id"),
        {"comment": "Multilingual content for persons"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    language_code: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="BCP 47 language tag (e.g. pl, en, la)"
    )
    canonical_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    prayers: Mapped[str | None] = mapped_column(Text, nullable=True)
    iconographic_attributes: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="translations")


# ==============================================================================
# POPE
# ==============================================================================


class Pope(BaseModel, Base):
    """
    Pontiff of the Catholic Church.

    The Pope is linked to a Person record (they may also be a saint).
    This table captures the pontificate-specific information.
    """

    __tablename__ = "popes"
    __table_args__ = (
        UniqueConstraint("papal_name", "pontificate_start", name="uq_pope_pontificate"),
        {"comment": "Popes – pontiffs of the Catholic Church"},
    )

    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        comment="Link to Person record if the pope is also canonized/beatified",
    )
    papal_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Full papal name (e.g. John Paul II)"
    )
    pontificate_start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pontificate_end: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pontificate_start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pontificate_end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    regnal_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Regnal number (e.g. 2 for John Paul II)"
    )
    birth_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    nationality_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person | None"] = relationship("Person")


# ==============================================================================
# CANONIZATION
# ==============================================================================


class Canonization(BaseModel, Base):
    """Record of a person's formal canonization."""

    __tablename__ = "canonizations"
    __table_args__ = (
        UniqueConstraint("person_id", name="uq_canonization_person"),
        {"comment": "Canonization records"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    pope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("popes.id", ondelete="SET NULL"),
        nullable=True,
    )
    canonization_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    canonization_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    decree_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    acta_reference: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Reference to Acta Apostolicae Sedis"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="canonization")
    pope: Mapped["Pope | None"] = relationship("Pope")
    place: Mapped["Place | None"] = relationship("Place")


# ==============================================================================
# BEATIFICATION
# ==============================================================================


class Beatification(BaseModel, Base):
    """Record of a person's beatification."""

    __tablename__ = "beatifications"
    __table_args__ = (
        UniqueConstraint("person_id", name="uq_beatification_person"),
        {"comment": "Beatification records"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    pope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("popes.id", ondelete="SET NULL"),
        nullable=True,
    )
    beatification_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    beatification_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    decree_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="beatification")
    pope: Mapped["Pope | None"] = relationship("Pope")
    place: Mapped["Place | None"] = relationship("Place")


# ==============================================================================
# MIRACLE
# ==============================================================================


class Miracle(BaseModel, Base):
    """A miracle attributed to a person's intercession."""

    __tablename__ = "miracles"
    __table_args__ = (
        Index("ix_miracles_person_id", "person_id"),
        Index("ix_miracles_status", "verification_status"),
        {"comment": "Miracles attributed to persons"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=MiracleStatus.REPORTED,
    )
    used_for_beatification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    used_for_canonization: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="miracles")
    place: Mapped["Place | None"] = relationship("Place")


# ==============================================================================
# PATRONAGE
# ==============================================================================


class Patronage(BaseModel, Base):
    """A patronage attributed to a person (patron of a country, city, profession, etc.)."""

    __tablename__ = "patronages"
    __table_args__ = (
        Index("ix_patronages_person_id", "person_id"),
        Index("ix_patronages_type", "patronage_type"),
        {"comment": "Patronages attributed to persons"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    patronage_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="country/city/diocese/profession/illness/other",
    )
    name_pl: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="What/who is patronized (Polish)"
    )
    name_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
        comment="Country referenced if type=country",
    )
    is_official: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if confirmed by official Church declaration",
    )

    person: Mapped["Person"] = relationship("Person", back_populates="patronages")


# ==============================================================================
# RELIC
# ==============================================================================


class Relic(BaseModel, Base):
    """A relic of a person kept in a specific church."""

    __tablename__ = "relics"
    __table_args__ = (
        Index("ix_relics_person_id", "person_id"),
        {"comment": "Relics of persons"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    relic_class: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="Relic class: 1st (body part), 2nd (object), 3rd (touched)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    church_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("churches.id", ondelete="SET NULL"),
        nullable=True,
    )
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_authenticated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    authentication_document: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship("Person")


# ==============================================================================
# PERSON QUOTE
# ==============================================================================


class PersonQuote(BaseModel, Base):
    """A notable quote attributed to or about a person."""

    __tablename__ = "person_quotes"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    quote_pl: Mapped[str] = mapped_column(Text, nullable=False)
    quote_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_la: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_attributed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True = said by the person; False = said about them",
    )

    person: Mapped["Person"] = relationship("Person")


# ==============================================================================
# PERSON RELATIONSHIP
# ==============================================================================


class PersonRelationship(BaseModel, Base):
    """Relationship between two persons in the hagiographic catalogue."""

    __tablename__ = "person_relationships"
    __table_args__ = (
        Index("ix_person_relationships_a", "person_a_id"),
        Index("ix_person_relationships_b", "person_b_id"),
        {"comment": "Relationships between persons"},
    )

    person_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="RelationshipType enum value",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_bidirectional: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True = the relationship is mutual",
    )

    person_a: Mapped["Person"] = relationship(
        "Person", foreign_keys=[person_a_id], back_populates="relationships_as_a"
    )
    person_b: Mapped["Person"] = relationship(
        "Person", foreign_keys=[person_b_id], back_populates="relationships_as_b"
    )


# ==============================================================================
# PERSON VERSION (audit snapshot)
# ==============================================================================


class PersonVersion(Base):
    """
    Immutable snapshot of a Person record at a given version.

    Created on every update. Enables full history browsing and rollback.
    """

    __tablename__ = "person_versions"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "version_number", name="uq_person_version_number"
        ),
        Index("ix_person_versions_person_id", "person_id"),
        {"comment": "Versioned snapshots of person records"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="Full serialized Person record at this version"
    )
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    person: Mapped["Person"] = relationship("Person", back_populates="versions")


# ==============================================================================
# MANY-TO-MANY ASSOCIATIONS
# ==============================================================================


class PersonOccupation(Base):
    """Association: Person ↔ Occupation."""

    __tablename__ = "person_occupations"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    occupation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("occupations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="occupations")
    occupation: Mapped["Occupation"] = relationship("Occupation")


class PersonOrder(Base):
    """Association: Person ↔ ReligiousOrder."""

    __tablename__ = "person_orders"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("religious_orders.id", ondelete="CASCADE"),
        primary_key=True,
    )
    entry_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exit_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_founder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    person: Mapped["Person"] = relationship("Person", back_populates="orders")
    order: Mapped["ReligiousOrder"] = relationship("ReligiousOrder")


class PersonCategory(Base):
    """Association: Person ↔ Category."""

    __tablename__ = "person_categories"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="categories")
    category: Mapped["Category"] = relationship("Category")


class PersonTag(Base):
    """Association: Person ↔ Tag."""

    __tablename__ = "person_tags"

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    person: Mapped["Person"] = relationship("Person", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag")
