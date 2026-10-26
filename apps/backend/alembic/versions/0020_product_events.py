"""Add bounded, privacy-preserving product analytics events."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_product_events"
down_revision: str | None = "0019_person_slug_redirects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the bounded raw-event table and retention indexes."""
    op.create_table(
        "product_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "retention_until",
            sa.DateTime(timezone=True),
            server_default=sa.text("now() + interval '90 days'"),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(length=50), nullable=False),
        sa.Column("query_class", sa.String(length=32), nullable=True),
        sa.Column("session_id_hash", sa.String(length=64), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="Privacy-preserving product analytics events with bounded retention",
    )
    op.create_index(
        "ix_product_events_created_at_event_name",
        "product_events",
        ["created_at", "event_name"],
    )
    op.create_index(
        "ix_product_events_session_id_hash",
        "product_events",
        ["session_id_hash"],
    )


def downgrade() -> None:
    """Drop the product analytics event table."""
    op.drop_index("ix_product_events_session_id_hash", table_name="product_events")
    op.drop_index("ix_product_events_created_at_event_name", table_name="product_events")
    op.drop_table("product_events")
