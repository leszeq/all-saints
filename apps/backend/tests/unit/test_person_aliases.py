"""Regression coverage for searchable person aliases."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from src.domain.hagiography.models import PersonName
from src.domain.hagiography.person_names import normalize_person_name

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0016_person_names.py"


def test_person_name_normalization_is_accent_and_punctuation_insensitive() -> None:
    assert normalize_person_name("  Św. Karol Józef Wojtyła  ") == "sw karol jozef wojtyla"
    assert normalize_person_name("J.P. II") == "j p ii"


def test_person_name_model_enforces_normalized_uniqueness_and_search_indexes() -> None:
    constraints = {constraint.name for constraint in PersonName.__table__.constraints}
    indexes = {index.name for index in PersonName.__table__.indexes}

    assert "uq_person_name_normalized" in constraints
    assert "ix_person_names_normalized_value" in indexes
    assert "ix_person_names_value_trgm" in indexes


def test_alias_migration_extends_the_single_history_and_backfills_names() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    source = MIGRATION.read_text(encoding="utf-8")

    migration = scripts.get_revision("0016_person_names")
    successor = scripts.get_revision("0017_translation_workflow_rbac")
    assert migration is not None
    assert successor is not None
    assert successor.down_revision == migration.revision
    assert len(scripts.get_heads()) == 1
    assert migration.down_revision == "0015_drop_legacy_embedding"
    assert "original_name AS value" in source
    assert "religious_name AS value" in source
    assert "ON CONFLICT (person_id, normalized_value) DO NOTHING" in source
    assert "ix_person_translations_canonical_name_trgm" in source
