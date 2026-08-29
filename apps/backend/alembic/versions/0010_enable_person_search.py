"""Maintain weighted person full-text search and trigram indexes.

Revision ID: 0010_enable_person_search
Revises: 0009_expand_countries
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_enable_person_search"
down_revision: str | None = "0009_expand_countries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEARCH_VECTOR_EXPRESSION = """
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.canonical_name, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.canonical_name_en, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.latin_name, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.original_name, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.surnames, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.religious_name, ''))), 'A') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.summary_pl, ''))), 'B') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.iconographic_attributes, ''))), 'B') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.prayers, ''))), 'C') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.works, ''))), 'C') ||
    setweight(to_tsvector('simple', unaccent(coalesce(NEW.biography_pl, ''))), 'D')
"""


def _create_trigram_index(table: str, column: str) -> None:
    op.create_index(
        f"ix_{table}_{column}_trgm",
        table,
        [column],
        postgresql_using="gin",
        postgresql_ops={column: "gin_trgm_ops"},
    )


def upgrade() -> None:
    """Install search maintenance trigger, backfill data, and add fuzzy indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION saints_person_search_vector_update()
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
        CREATE TRIGGER trg_persons_search_vector
        BEFORE INSERT OR UPDATE OF
            canonical_name, canonical_name_en, latin_name, original_name,
            surnames, religious_name, summary_pl, biography_pl,
            iconographic_attributes, prayers, works
        ON persons
        FOR EACH ROW
        EXECUTE FUNCTION saints_person_search_vector_update()
        """
    )
    op.execute("UPDATE persons SET canonical_name = canonical_name")

    for column in ("canonical_name", "canonical_name_en", "latin_name"):
        _create_trigram_index("persons", column)
    for column in ("name_pl", "name_en", "description"):
        _create_trigram_index("patronages", column)


def downgrade() -> None:
    """Remove trigger and fuzzy indexes while preserving the base FTS column."""
    for column in ("description", "name_en", "name_pl"):
        op.drop_index(f"ix_patronages_{column}_trgm", table_name="patronages")
    for column in ("latin_name", "canonical_name_en", "canonical_name"):
        op.drop_index(f"ix_persons_{column}_trgm", table_name="persons")

    op.execute("DROP TRIGGER IF EXISTS trg_persons_search_vector ON persons")
    op.execute("DROP FUNCTION IF EXISTS saints_person_search_vector_update()")
    op.execute("UPDATE persons SET search_vector = NULL")
