"""Executable checks for the translation-workflow RBAC migration."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0017_translation_workflow_rbac.py"


def test_translation_rbac_migration_is_ordered_and_reversible() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    source = MIGRATION.read_text(encoding="utf-8")

    migration = scripts.get_revision("0017_translation_workflow_rbac")
    assert migration is not None
    assert scripts.get_current_head() == migration.revision
    assert len(scripts.get_heads()) == 1
    assert 'down_revision: str | None = "0016_person_names"' in source
    assert "translations', 'delete" in source
    assert '"editor", "translations", "read"' in source
    assert '"reviewer", "translations", "read"' in source
    assert '"translator", "translations", "delete"' in source
    assert "def downgrade()" in source
