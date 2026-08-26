"""Expand religious orders with editorial content and membership roles.

Revision ID: 0006_expand_religious_orders
Revises: 0005_enrich_liturgical_feasts
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0006_expand_religious_orders"
down_revision: str | None = "0005_enrich_liturgical_feasts"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Add public catalogue content and richer person memberships."""
    op.add_column("religious_orders", sa.Column("slug", sa.String(length=500), nullable=True))
    op.add_column(
        "religious_orders",
        sa.Column(
            "community_type",
            sa.String(length=40),
            nullable=False,
            server_default="religious_order",
        ),
    )
    op.add_column(
        "religious_orders", sa.Column("spiritual_family", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "religious_orders", sa.Column("founder_name", sa.String(length=500), nullable=True)
    )
    op.add_column("religious_orders", sa.Column("history", sa.Text(), nullable=True))
    op.add_column("religious_orders", sa.Column("mission", sa.Text(), nullable=True))
    op.add_column("religious_orders", sa.Column("motto", sa.String(length=300), nullable=True))
    op.add_column(
        "religious_orders", sa.Column("website_url", sa.String(length=2000), nullable=True)
    )
    op.add_column(
        "religious_orders", sa.Column("source_title", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "religious_orders", sa.Column("source_url", sa.String(length=2000), nullable=True)
    )
    op.add_column(
        "religious_orders",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "religious_orders",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.execute("UPDATE religious_orders SET slug = id::text WHERE slug IS NULL")
    op.alter_column("religious_orders", "slug", nullable=False)
    op.create_index("uq_religious_orders_slug", "religious_orders", ["slug"], unique=True)
    op.create_index(
        "ix_religious_orders_spiritual_family",
        "religious_orders",
        ["spiritual_family"],
        unique=False,
    )
    op.create_index(
        "ix_religious_orders_featured", "religious_orders", ["is_featured"], unique=False
    )

    op.add_column(
        "person_orders",
        sa.Column("membership_type", sa.String(length=40), nullable=False, server_default="member"),
    )
    op.add_column("person_orders", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove public catalogue content and membership roles."""
    op.drop_column("person_orders", "notes")
    op.drop_column("person_orders", "membership_type")

    op.drop_index("ix_religious_orders_featured", table_name="religious_orders")
    op.drop_index("ix_religious_orders_spiritual_family", table_name="religious_orders")
    op.drop_index("uq_religious_orders_slug", table_name="religious_orders")
    op.drop_column("religious_orders", "sort_order")
    op.drop_column("religious_orders", "is_featured")
    op.drop_column("religious_orders", "source_url")
    op.drop_column("religious_orders", "source_title")
    op.drop_column("religious_orders", "website_url")
    op.drop_column("religious_orders", "motto")
    op.drop_column("religious_orders", "mission")
    op.drop_column("religious_orders", "history")
    op.drop_column("religious_orders", "founder_name")
    op.drop_column("religious_orders", "spiritual_family")
    op.drop_column("religious_orders", "community_type")
    op.drop_column("religious_orders", "slug")
