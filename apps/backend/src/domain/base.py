"""
SQLAlchemy 2.0 declarative base and shared mixins.

All domain models inherit from these base classes to ensure
consistent columns, soft-delete behaviour, and versioning.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column


# ==============================================================================
# DECLARATIVE BASE
# ==============================================================================


class Base(DeclarativeBase):
    """
    Custom declarative base with type annotation support.

    All ORM models must inherit from this class.
    """

    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
    }


# ==============================================================================
# MIXINS
# ==============================================================================


class UUIDMixin:
    """Provides a UUID primary key generated server-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        index=True,
    )


class TimestampMixin:
    """
    Provides created_at and updated_at audit timestamps.

    Both columns are set and maintained automatically by the database.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    """
    Provides soft-delete capability via deleted_at timestamp.

    Records are never physically deleted – deleted_at is set instead.
    Use ``is_deleted`` property to check status, and the
    ``filter_active()`` query helper to exclude deleted records.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """True if this record has been soft-deleted."""
        return self.deleted_at is not None


class VersionMixin:
    """
    Provides optimistic locking via a version counter.

    Incremented by the application layer on every update.
    Used to detect concurrent modification conflicts.
    """

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )


class BaseModel(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """
    Composite base mixin for all domain entities.

    Provides:
    - UUID primary key
    - created_at / updated_at timestamps
    - deleted_at (soft delete)
    - version (optimistic locking)
    """

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize model to dictionary (for audit logs / snapshots)."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
