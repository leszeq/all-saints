"""Add reviewed patronage concepts, aliases, and person assignments."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0022_patronage_concepts"
down_revision: str | None = "0021_product_event_aggregates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column[object]]:
    """Return columns shared by reviewable concept records."""
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    ]


def upgrade() -> None:
    """Create tables and preserve existing patronage rows as reviewable drafts."""
    op.create_table(
        "patronage_concepts",
        *_base_columns(),
        sa.Column("slug", sa.String(length=300), nullable=False),
        sa.Column("patronage_type", sa.String(length=50), nullable=False),
        sa.Column("name_pl", sa.String(length=500), nullable=False),
        sa.Column("name_en", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column(
            "reviewed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_patronage_concepts_slug"),
        comment="Reviewed canonical patronage concepts",
    )
    op.create_index("ix_patronage_concepts_status", "patronage_concepts", ["status"])
    op.create_index("ix_patronage_concepts_type", "patronage_concepts", ["patronage_type"])
    op.create_index("ix_patronage_concepts_name_pl", "patronage_concepts", ["name_pl"])

    op.create_table(
        "concept_aliases",
        *_base_columns(),
        sa.Column(
            "concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patronage_concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("normalized_value", sa.String(length=500), nullable=False),
        sa.Column("language_code", sa.String(length=10), server_default=sa.text("'pl'"), nullable=False),
        sa.Column("alias_kind", sa.String(length=20), server_default=sa.text("'common'"), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "concept_id",
            "normalized_value",
            "language_code",
            name="uq_concept_aliases_concept_value_language",
        ),
        comment="Reviewed aliases for canonical concepts",
    )
    op.create_index("ix_concept_aliases_normalized_value", "concept_aliases", ["normalized_value"])

    op.create_table(
        "person_patronage_concepts",
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patronage_concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_patronage_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patronages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_patronage_type", sa.String(length=50), nullable=False),
        sa.Column("source_label", sa.String(length=500), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False),
        sa.Column(
            "assigned_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("person_id", "concept_id"),
        comment="Reviewed person-to-patronage concept assignments",
    )
    op.create_index("ix_person_patronage_concepts_status", "person_patronage_concepts", ["status"])
    op.create_index("ix_person_patronage_concepts_source", "person_patronage_concepts", ["source_patronage_id"])

    # Keep every legacy label and source row traceable.  Concepts remain drafts
    # until an editor explicitly reviews them; punctuation collisions receive a
    # deterministic hash suffix instead of being silently merged.
    op.execute(
        """
        WITH source AS (
          SELECT
            patronage_type,
            name_pl,
            min(name_en) AS name_en,
            min(description) AS description,
            trim(both '-' FROM regexp_replace(
              regexp_replace(unaccent(lower(patronage_type || '-' || name_pl)), '[^a-z0-9]+', '-', 'g'),
              '(^-+|-+$)', '', 'g'
            )) AS base_slug
          FROM patronages
          WHERE deleted_at IS NULL
          GROUP BY patronage_type, name_pl
        ), ranked AS (
          SELECT
            source.*,
            count(*) OVER (PARTITION BY base_slug) AS slug_count
          FROM source
        )
        INSERT INTO patronage_concepts
          (id, created_at, updated_at, version, slug, patronage_type, name_pl, name_en, description, status)
        SELECT
          gen_random_uuid(), now(), now(), 1,
          CASE
            WHEN slug_count = 1 AND base_slug <> '' THEN base_slug
            ELSE base_slug || '-' || substr(md5(patronage_type || '|' || name_pl), 1, 8)
          END,
          patronage_type, name_pl, name_en, description, 'draft'
        FROM ranked
        ON CONFLICT (slug) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO person_patronage_concepts
          (person_id, concept_id, source_patronage_id, source_patronage_type,
           source_label, evidence_reference, status)
        SELECT
          patronage.person_id,
          concept.id,
          patronage.id,
          patronage.patronage_type,
          patronage.name_pl,
          'Backfill z Patronage #' || patronage.id::text,
          'pending'
        FROM patronages AS patronage
        JOIN patronage_concepts AS concept
          ON concept.patronage_type = patronage.patronage_type
         AND concept.name_pl = patronage.name_pl
        WHERE patronage.deleted_at IS NULL
        ON CONFLICT (person_id, concept_id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Drop concept assignments, aliases, and canonical concepts."""
    op.drop_index("ix_person_patronage_concepts_source", table_name="person_patronage_concepts")
    op.drop_index("ix_person_patronage_concepts_status", table_name="person_patronage_concepts")
    op.drop_table("person_patronage_concepts")
    op.drop_index("ix_concept_aliases_normalized_value", table_name="concept_aliases")
    op.drop_table("concept_aliases")
    op.drop_index("ix_patronage_concepts_name_pl", table_name="patronage_concepts")
    op.drop_index("ix_patronage_concepts_type", table_name="patronage_concepts")
    op.drop_index("ix_patronage_concepts_status", table_name="patronage_concepts")
    op.drop_table("patronage_concepts")
