"""Regression coverage for PostgreSQL person-search infrastructure."""

from __future__ import annotations

from pathlib import Path

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0010_enable_person_search.py"


def test_search_migration_is_reversible_and_backfills_existing_people() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision: str | None = "0009_expand_countries"' in source
    assert "CREATE TRIGGER trg_persons_search_vector" in source
    assert "UPDATE persons SET canonical_name = canonical_name" in source
    assert "DROP TRIGGER IF EXISTS trg_persons_search_vector" in source
    assert "DROP FUNCTION IF EXISTS saints_person_search_vector_update()" in source


def test_search_document_contains_weighted_polish_content() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert "unaccent(coalesce(NEW.canonical_name" in source
    assert "setweight" in source
    assert "NEW.biography_pl" in source
    assert "NEW.iconographic_attributes" in source
    assert "gin_trgm_ops" in source
