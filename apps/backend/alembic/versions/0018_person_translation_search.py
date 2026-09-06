"""Add weighted full-text search for active person translations.

Revision ID: 0018_person_translation_search
Revises: 0017_translation_workflow_rbac
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0018_person_translation_search"
down_revision: str | None = "0017_translation_workflow_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_VECTOR_EXPRESSION = """
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.canonical_name, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.summary, ''))), 'B') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.iconographic_attributes, ''))), 'B') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.prayers, ''))), 'C') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.biography, ''))), 'D')
"""


def upgrade() -> None:
    """Install trigger-maintained search documents and active-row indexes."""
    op.alter_column(
        "person_translations",
        "language_code",
        existing_type=sa.String(length=10),
        type_=sa.String(length=35),
        existing_nullable=False,
    )
    op.add_column(
        "person_translations",
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION saints_person_translation_search_vector_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.search_vector := {SEARCH_VECTOR_EXPRESSION};
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_person_translations_search_vector
        BEFORE INSERT OR UPDATE OF
            canonical_name, summary, biography, prayers, iconographic_attributes
        ON person_translations
        FOR EACH ROW
        EXECUTE FUNCTION saints_person_translation_search_vector_update()
        """
    )
    op.execute("UPDATE person_translations SET canonical_name = canonical_name")
    op.create_index(
        "ix_person_translations_search_vector",
        "person_translations",
        ["search_vector"],
        postgresql_using="gin",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        "ix_person_translations_canonical_name_trgm",
        table_name="person_translations",
    )
    op.create_index(
        "ix_person_translations_canonical_name_trgm",
        "person_translations",
        ["canonical_name"],
        postgresql_using="gin",
        postgresql_ops={"canonical_name": "gin_trgm_ops"},
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    """Restore name-only translation search without deleting content."""
    op.drop_index(
        "ix_person_translations_canonical_name_trgm",
        table_name="person_translations",
    )
    op.create_index(
        "ix_person_translations_canonical_name_trgm",
        "person_translations",
        ["canonical_name"],
        postgresql_using="gin",
        postgresql_ops={"canonical_name": "gin_trgm_ops"},
    )
    op.drop_index(
        "ix_person_translations_search_vector",
        table_name="person_translations",
    )
    op.execute("DROP TRIGGER IF EXISTS trg_person_translations_search_vector ON person_translations")
    op.execute("DROP FUNCTION IF EXISTS saints_person_translation_search_vector_update()")
    op.drop_column("person_translations", "search_vector")
    op.alter_column(
        "person_translations",
        "language_code",
        existing_type=sa.String(length=35),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
