"""
Liturgy domain models.

Covers: LiturgicalCalendar, Feast, PersonFeast (association).
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.base import Base, BaseModel


# ==============================================================================
# ENUMS
# ==============================================================================


class FeastRank(StrEnum):
    """Liturgical rank of a feast."""

    SOLEMNITY = "solemnity"       # Uroczystość
    FEAST = "feast"               # Święto
    MEMORIAL = "memorial"         # Wspomnienie obowiązkowe
    OPT_MEMORIAL = "opt_memorial" # Wspomnienie dowolne
    COMMEMORATION = "commemoration"


class CalendarScope(StrEnum):
    """Geographic / rite scope of a liturgical calendar."""

    UNIVERSAL = "universal"       # Roman Rite – universal
    NATIONAL = "national"         # National calendar
    DIOCESAN = "diocesan"
    RELIGIOUS = "religious"       # Religious order calendar
    LOCAL = "local"


# ==============================================================================
# LITURGICAL CALENDAR
# ==============================================================================


class LiturgicalCalendar(BaseModel, Base):
    """
    A specific liturgical calendar (Roman, Polish, Dominican, etc.).

    Multiple calendars can overlap – a feast may appear in several.
    """

    __tablename__ = "liturgical_calendars"
    __table_args__ = (
        UniqueConstraint("code", name="uq_liturgical_calendar_code"),
        {"comment": "Liturgical calendars"},
    )

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="Unique code (e.g. 'roman_universal')"
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    rite: Mapped[str] = mapped_column(
        String(100), nullable=False, default="roman", comment="Rite name"
    )
    scope: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CalendarScope.UNIVERSAL
    )
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="SET NULL"),
        nullable=True,
        comment="Country if scope=national",
    )
    religious_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("religious_orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Religious order if scope=religious",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    feasts: Mapped[list["Feast"]] = relationship("Feast", back_populates="calendar")


# ==============================================================================
# FEAST
# ==============================================================================


class Feast(BaseModel, Base):
    """
    A liturgical feast day for a person on a specific calendar.

    A person may have different feast dates in different calendars
    (e.g. universal vs. Polish national calendar).
    """

    __tablename__ = "feasts"
    __table_args__ = (
        Index("ix_feasts_person_id", "person_id"),
        Index("ix_feasts_calendar_id", "calendar_id"),
        Index("ix_feasts_day_of_year", "day_of_year"),
        Index("ix_feasts_month", "month"),
        {"comment": "Liturgical feast days"},
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("liturgical_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Date (fixed or moveable)
    month: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="Month (1-12) for fixed feasts"
    )
    day: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True, comment="Day of month for fixed feasts"
    )
    day_of_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Pre-computed day of year for fixed feasts (1-366)",
    )
    date_note: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Human-readable date (e.g. 'First Sunday of Advent')",
    )
    is_moveable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="True for moveable feasts"
    )

    # Liturgical details
    rank: Mapped[str] = mapped_column(
        String(30), nullable=False, default=FeastRank.MEMORIAL
    )
    liturgical_color: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Metadata
    is_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    person: Mapped["Person"] = relationship("Person")
    calendar: Mapped["LiturgicalCalendar"] = relationship(
        "LiturgicalCalendar", back_populates="feasts"
    )


# Fix forward reference
from src.domain.hagiography.models import Person  # noqa: E402
