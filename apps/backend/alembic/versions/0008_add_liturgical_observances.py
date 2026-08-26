"""Separate non-person liturgical observances from hagiographic persons.

Revision ID: 0008_add_liturgical_observances
Revises: 0007_register_roman_martyrology
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_add_liturgical_observances"
down_revision: str | None = "0007_register_roman_martyrology"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

MARY_SLUG = "najswietsza-maryja-panna-czestochowska"


def upgrade() -> None:
    """Create observances and migrate the existing Częstochowa Marian title."""
    op.create_table(
        "liturgical_observances",
        sa.Column(
            "slug",
            sa.String(length=300),
            nullable=False,
        ),
        sa.Column("title_pl", sa.String(length=500), nullable=False),
        sa.Column("title_en", sa.String(length=500), nullable=True),
        sa.Column("latin_title", sa.String(length=500), nullable=True),
        sa.Column(
            "observance_type",
            sa.String(length=30),
            nullable=False,
            server_default="other",
        ),
        sa.Column("summary_pl", sa.Text(), nullable=True),
        sa.Column("description_pl", sa.Text(), nullable=True),
        sa.Column("iconographic_attributes", sa.Text(), nullable=True),
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_liturgical_observance_slug"),
        comment="Non-person liturgical observances",
    )
    op.create_index(
        "ix_liturgical_observances_deleted_at",
        "liturgical_observances",
        ["deleted_at"],
    )
    op.create_index("ix_liturgical_observances_id", "liturgical_observances", ["id"])
    op.create_index(
        "ix_liturgical_observances_type",
        "liturgical_observances",
        ["observance_type"],
    )

    op.add_column(
        "feasts",
        sa.Column("observance_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_feasts_observance_id_liturgical_observances",
        "feasts",
        "liturgical_observances",
        ["observance_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_feasts_observance_id", "feasts", ["observance_id"])
    op.alter_column("feasts", "person_id", existing_type=postgresql.UUID(), nullable=True)

    op.execute(
        sa.text(
            """
            INSERT INTO liturgical_observances (
                slug, title_pl, title_en, latin_title, observance_type,
                summary_pl, description_pl, iconographic_attributes, is_featured
            )
            SELECT
                slug, canonical_name, canonical_name_en, latin_name, 'marian',
                summary_pl, biography_pl, iconographic_attributes, is_featured
            FROM persons
            WHERE slug = :slug
            ON CONFLICT (slug) DO NOTHING
            """
        ).bindparams(slug=MARY_SLUG)
    )
    op.execute(
        sa.text(
            """
            UPDATE feasts AS feast
            SET observance_id = observance.id,
                person_id = NULL,
                updated_at = now()
            FROM persons AS person
            CROSS JOIN liturgical_observances AS observance
            WHERE feast.person_id = person.id
              AND person.slug = :slug
              AND observance.slug = :slug
            """
        ).bindparams(slug=MARY_SLUG)
    )
    op.execute(
        sa.text(
            """
            UPDATE persons
            SET deleted_at = COALESCE(deleted_at, now()),
                updated_at = now()
            WHERE slug = :slug
            """
        ).bindparams(slug=MARY_SLUG)
    )

    op.drop_index("uq_feasts_active_person_calendar_date", table_name="feasts")
    op.create_index(
        "uq_feasts_active_person_calendar_date",
        "feasts",
        ["person_id", "calendar_id", "month", "day"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND person_id IS NOT NULL "
            "AND month IS NOT NULL AND day IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_feasts_active_observance_calendar_date",
        "feasts",
        ["observance_id", "calendar_id", "month", "day"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND observance_id IS NOT NULL "
            "AND month IS NOT NULL AND day IS NOT NULL"
        ),
    )
    op.create_check_constraint(
        "ck_feasts_exactly_one_target",
        "feasts",
        "(person_id IS NOT NULL) <> (observance_id IS NOT NULL)",
    )


def downgrade() -> None:
    """Restore the legacy person-only feast representation."""
    op.drop_constraint("ck_feasts_exactly_one_target", "feasts", type_="check")
    op.drop_index("uq_feasts_active_observance_calendar_date", table_name="feasts")
    op.drop_index("uq_feasts_active_person_calendar_date", table_name="feasts")

    op.execute(
        sa.text(
            """
            UPDATE persons
            SET deleted_at = NULL,
                updated_at = now()
            WHERE slug = :slug
            """
        ).bindparams(slug=MARY_SLUG)
    )
    op.execute(
        sa.text(
            """
            UPDATE feasts AS feast
            SET person_id = person.id,
                observance_id = NULL,
                updated_at = now()
            FROM persons AS person
            JOIN liturgical_observances AS observance ON observance.slug = person.slug
            WHERE feast.observance_id = observance.id
              AND person.slug = :slug
            """
        ).bindparams(slug=MARY_SLUG)
    )
    op.execute("DELETE FROM feasts WHERE observance_id IS NOT NULL")

    op.alter_column("feasts", "person_id", existing_type=postgresql.UUID(), nullable=False)
    op.drop_index("ix_feasts_observance_id", table_name="feasts")
    op.drop_constraint(
        "fk_feasts_observance_id_liturgical_observances",
        "feasts",
        type_="foreignkey",
    )
    op.drop_column("feasts", "observance_id")
    op.create_index(
        "uq_feasts_active_person_calendar_date",
        "feasts",
        ["person_id", "calendar_id", "month", "day"],
        unique=True,
        postgresql_where=sa.text(
            "deleted_at IS NULL AND month IS NOT NULL AND day IS NOT NULL"
        ),
    )

    op.drop_index("ix_liturgical_observances_type", table_name="liturgical_observances")
    op.drop_index("ix_liturgical_observances_id", table_name="liturgical_observances")
    op.drop_index("ix_liturgical_observances_deleted_at", table_name="liturgical_observances")
    op.drop_table("liturgical_observances")
