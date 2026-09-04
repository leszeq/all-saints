"""Regression coverage for a single pgvector embedding source of truth."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from src.domain.hagiography.embedding_model import PersonEmbedding
from src.domain.hagiography.models import Person

MIGRATION = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "0015_remove_legacy_person_embeddings.py"
)


def test_person_embedding_table_is_the_only_vector_storage() -> None:
    assert "embedding_vector" not in Person.__table__.c
    assert "embedding" in PersonEmbedding.__table__.c


def test_legacy_column_removal_is_guarded_and_reversible() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    source = MIGRATION.read_text(encoding="utf-8")

    assert scripts.get_current_head() == "0015_drop_legacy_embedding"
    assert 'down_revision: str | None = "0014_person_version_changed_at"' in source
    assert "WHERE embedding_vector IS NOT NULL" in source
    assert 'op.drop_column("persons", "embedding_vector")' in source
    assert '"embedding_vector"' in source
