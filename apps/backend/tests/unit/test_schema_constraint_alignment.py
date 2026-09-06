"""Regression coverage for domain constraint and index alignment."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import UniqueConstraint

from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography.models import Person
from src.domain.identity.models import AuditLog, RolePermission, UserRole
from src.domain.sources.models import Image

MIGRATION = Path(__file__).parents[2] / "alembic" / "versions" / "0012_align_domain_indexes.py"


def _index(table: object, name: str):
    return next(index for index in table.indexes if index.name == name)


def test_rbac_assignments_rely_on_their_composite_primary_keys() -> None:
    for table, columns in (
        (RolePermission.__table__, {"role_id", "permission_id"}),
        (UserRole.__table__, {"user_id", "role_id"}),
    ):
        assert {column.name for column in table.primary_key.columns} == columns
        assert not any(
            isinstance(constraint, UniqueConstraint)
            and {column.name for column in constraint.columns} == columns
            for constraint in table.constraints
        )


def test_existing_slug_rules_are_represented_like_the_database() -> None:
    person_slug_constraints = [
        constraint
        for constraint in Person.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"slug"}
    ]
    assert len(person_slug_constraints) == 1
    assert _index(Person.__table__, "ix_persons_slug").unique is False
    assert _index(ReligiousOrder.__table__, "uq_religious_orders_slug").unique is True


def test_primary_person_image_partial_index_is_in_metadata() -> None:
    index = _index(Image.__table__, "uq_images_active_primary_person")

    assert index.unique is True
    predicate = str(index.dialect_options["postgresql"]["where"])
    assert "person_id IS NOT NULL" in predicate
    assert "is_primary = true" in predicate
    assert "deleted_at IS NULL" in predicate


def test_audit_action_index_has_a_reversible_migration() -> None:
    assert _index(AuditLog.__table__, "ix_audit_logs_action").unique is False

    source = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision: str | None = "0011_align_base_indexes"' in source
    assert 'op.create_index("ix_audit_logs_action"' in source
    assert 'op.drop_index("ix_audit_logs_action"' in source
