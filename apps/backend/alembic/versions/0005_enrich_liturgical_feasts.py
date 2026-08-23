"""Add editorial priority, provenance, and uniqueness to liturgical feasts.

Revision ID: 0005_enrich_liturgical_feasts
Revises: 0004_unique_primary_person_image
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0005_enrich_liturgical_feasts"
down_revision: str | None = "0004_unique_primary_person_image"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Extend feast records and protect active calendar assignments."""
    op.add_column(
        "feasts",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("feasts", sa.Column("source_title", sa.String(length=500), nullable=True))
    op.add_column("feasts", sa.Column("source_url", sa.String(length=2000), nullable=True))

    op.create_index("ix_feasts_month_day", "feasts", ["month", "day"], unique=False)
    op.create_index(
        "uq_feasts_active_person_calendar_date",
        "feasts",
        ["person_id", "calendar_id", "month", "day"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND month IS NOT NULL AND day IS NOT NULL"),
    )
    op.create_index(
        "uq_feasts_active_primary_calendar_date",
        "feasts",
        ["calendar_id", "month", "day"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND is_primary = true " "AND month IS NOT NULL AND day IS NOT NULL"
        ),
    )


def downgrade() -> None:
    """Remove feast provenance and primary-selection metadata."""
    op.drop_index("uq_feasts_active_primary_calendar_date", table_name="feasts")
    op.drop_index("uq_feasts_active_person_calendar_date", table_name="feasts")
    op.drop_index("ix_feasts_month_day", table_name="feasts")
    op.drop_column("feasts", "source_url")
    op.drop_column("feasts", "source_title")
    op.drop_column("feasts", "is_primary")
