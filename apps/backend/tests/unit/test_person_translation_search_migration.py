"""Schema and migration policy for translated-content full-text search."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from src.domain.hagiography.models import PersonTranslation

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0018_person_translation_search.py"


def test_translation_search_model_has_partial_gin_index() -> None:
    column = PersonTranslation.__table__.c.search_vector
    language_column = PersonTranslation.__table__.c.language_code
    index = next(
        index
        for index in PersonTranslation.__table__.indexes
        if index.name == "ix_person_translations_search_vector"
    )

    assert column.nullable is True
    assert language_column.type.length == 35
    assert index.dialect_options["postgresql"]["using"] == "gin"
    assert "deleted_at IS NULL" in str(index.dialect_options["postgresql"]["where"])


def test_translation_search_migration_is_single_head_reversible_and_backfilled() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    source = MIGRATION.read_text(encoding="utf-8")

    migration = scripts.get_revision("0018_person_translation_search")
    assert migration is not None
    assert scripts.get_current_head() == migration.revision
    assert len(scripts.get_heads()) == 1
    assert migration.down_revision == "0017_translation_workflow_rbac"
    assert "CREATE TRIGGER trg_person_translations_search_vector" in source
    assert "UPDATE person_translations SET canonical_name = canonical_name" in source
    assert "type_=sa.String(length=35)" in source
    assert "type_=sa.String(length=10)" in source
    assert 'postgresql_where=sa.text("deleted_at IS NULL")' in source
    assert "DROP FUNCTION IF EXISTS saints_person_translation_search_vector_update()" in source
