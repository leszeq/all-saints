"""Add daily, aggregate-only product analytics rows."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_product_event_aggregates"
down_revision: str | None = "0020_product_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the aggregate table used by the protected PM dashboard."""
    op.create_table(
        "product_event_daily_aggregates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("event_name", sa.String(length=50), nullable=False),
        sa.Column("query_class", sa.String(length=32), nullable=True),
        sa.Column("event_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("unique_sessions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("result_count_sum", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("zero_results_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("search_success_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "day",
            "event_name",
            "query_class",
            name="uq_product_event_daily_aggregate_dimension",
        ),
        comment="Daily product analytics aggregates; no raw session identifiers",
    )
    op.create_index(
        "ix_product_event_daily_aggregates_day",
        "product_event_daily_aggregates",
        ["day"],
    )


def downgrade() -> None:
    """Drop the daily aggregate table."""
    op.drop_index("ix_product_event_daily_aggregates_day", table_name="product_event_daily_aggregates")
    op.drop_table("product_event_daily_aggregates")
