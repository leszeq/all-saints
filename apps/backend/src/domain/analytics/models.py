"""Models and allowlists for privacy-preserving product analytics."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Date, DateTime, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.base import Base, UUIDMixin


class ProductEventName(StrEnum):
    """Events that are safe to aggregate for the public discovery funnel."""

    SEARCH_SUBMITTED = "search_submitted"
    SEARCH_RESULTS = "search_results"
    PROFILE_OPENED = "profile_opened"
    SOURCE_OPENED = "source_opened"
    RELATION_OPENED = "relation_opened"
    FILTER_APPLIED = "filter_applied"
    FEEDBACK_SUBMITTED = "feedback_submitted"


class ProductQueryClass(StrEnum):
    """Coarse query intent, without storing the entered query text."""

    NAME = "name"
    PATRONAGE = "patronage"
    OCCUPATION = "occupation"
    ORDER = "order"
    COUNTRY = "country"
    PERIOD = "period"
    FILTER = "filter"


class ProductFilterName(StrEnum):
    """Allowlisted discovery filters that can be counted in aggregates."""

    PERSON_TYPE = "person_type"
    GENDER = "gender"
    PERIOD = "period"
    PATRONAGE = "patronage"
    ORDER = "order"
    OCCUPATION = "occupation"
    BIRTH_COUNTRY = "birth_country"
    DEATH_COUNTRY = "death_country"
    NATIONALITY = "nationality"


class ProductSourceKind(StrEnum):
    """Coarse source category; URLs and titles are never accepted."""

    BIBLIOGRAPHY = "bibliography"
    HISTORICAL = "historical"
    IMAGE = "image"
    WEB = "web"


class ProductRelationKind(StrEnum):
    """Coarse relation category used for discovery funnel aggregates."""

    ORDER = "order"
    PATRONAGE = "patronage"
    OCCUPATION = "occupation"
    GEOGRAPHY = "geography"
    CALENDAR = "calendar"


class ProductFeedback(StrEnum):
    """Bounded feedback values; free-text comments are deliberately excluded."""

    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


class ProductEvent(UUIDMixin, Base):
    """A small, anonymous event row kept outside the domain catalogue."""

    __tablename__ = "product_events"
    __table_args__ = (
        Index("ix_product_events_created_at_event_name", "created_at", "event_name"),
        Index("ix_product_events_session_id_hash", "session_id_hash"),
        {"comment": "Privacy-preserving product analytics events with bounded retention"},
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    retention_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + interval '90 days'"),
        comment="Scheduled deletion boundary for the raw event row",
    )
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    query_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    session_id_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="HMAC-SHA256 of the client-generated anonymous session UUID",
    )
    properties: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Allowlisted aggregate dimensions only; no query text or PII",
    )


class ProductEventDailyAggregate(UUIDMixin, Base):
    """Daily aggregate rows exposed to the PM panel instead of raw events."""

    __tablename__ = "product_event_daily_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "day",
            "event_name",
            "query_class",
            name="uq_product_event_daily_aggregate_dimension",
        ),
        Index("ix_product_event_daily_aggregates_day", "day"),
        {"comment": "Daily product analytics aggregates; no raw session identifiers"},
    )

    day: Mapped[date] = mapped_column(Date, nullable=False)
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    query_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    unique_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    result_count_sum: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    zero_results_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    search_success_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
