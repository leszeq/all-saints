"""Executable policy checks for the RBAC data migration."""

from pathlib import Path

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0013_refine_editorial_rbac.py"


def test_rbac_migration_is_ordered_and_reversible() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision: str | None = "0012_align_domain_indexes"' in source
    assert "persons', 'submit" in source
    assert "persons', 'review" in source
    assert "trg_single_super_admin" in source
    assert "def downgrade()" in source


def test_rbac_migration_removes_identity_permissions_from_non_super_roles() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert "roles.name <> 'super_admin'" in source
    assert "permissions.resource IN ('users', 'roles')" in source
