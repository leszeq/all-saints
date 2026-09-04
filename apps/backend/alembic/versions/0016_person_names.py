"""Add searchable alternative person names.

Revision ID: 0016_person_names
Revises: 0015_drop_legacy_embedding
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016_person_names"
down_revision: str | None = "0015_drop_legacy_embedding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create alias storage, indexes, and backfill existing alternative names."""
    op.create_table(
        "person_names",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("normalized_value", sa.String(length=500), nullable=False),
        sa.Column("language_code", sa.String(length=10), server_default="pl", nullable=False),
        sa.Column("kind", sa.String(length=30), server_default="alias", nullable=False),
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "person_id",
            "normalized_value",
            name="uq_person_name_normalized",
        ),
        comment="Searchable alternative names for hagiographic persons",
    )
    op.create_index("ix_person_names_person_id", "person_names", ["person_id"])
    op.create_index(
        "ix_person_names_normalized_value",
        "person_names",
        ["normalized_value"],
    )
    op.create_index(
        "ix_person_names_value_trgm",
        "person_names",
        ["value"],
        postgresql_using="gin",
        postgresql_ops={"value": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_person_translations_canonical_name_trgm",
        "person_translations",
        ["canonical_name"],
        postgresql_using="gin",
        postgresql_ops={"canonical_name": "gin_trgm_ops"},
    )

    op.execute(
        """
        INSERT INTO person_names (
          id, person_id, value, normalized_value, language_code, kind,
          created_at, updated_at, deleted_at, version
        )
        SELECT
          gen_random_uuid(), person_id, value,
          btrim(regexp_replace(lower(unaccent(value)), '[^[:alnum:]]+', ' ', 'g')),
          'pl', kind,
          now(), now(), NULL, 1
        FROM (
          SELECT id AS person_id, original_name AS value, 'birth_name' AS kind
          FROM persons
          WHERE original_name IS NOT NULL AND btrim(original_name) <> ''
          UNION ALL
          SELECT id AS person_id, religious_name AS value, 'religious_name' AS kind
          FROM persons
          WHERE religious_name IS NOT NULL AND btrim(religious_name) <> ''
        ) existing_names
        ON CONFLICT (person_id, normalized_value) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove alias search while preserving scalar person-name fields."""
    op.drop_index(
        "ix_person_translations_canonical_name_trgm",
        table_name="person_translations",
    )
    op.drop_index("ix_person_names_value_trgm", table_name="person_names")
    op.drop_index("ix_person_names_normalized_value", table_name="person_names")
    op.drop_index("ix_person_names_person_id", table_name="person_names")
    op.drop_table("person_names")
