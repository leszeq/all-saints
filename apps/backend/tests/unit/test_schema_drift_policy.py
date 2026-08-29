"""Regression coverage for the executable-schema drift policy."""

from __future__ import annotations

from pathlib import Path

from src.domain.hagiography.models import Person

MIGRATION = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "0011_align_base_indexes.py"
)


def test_base_mixins_do_not_request_redundant_generic_indexes() -> None:
    assert Person.__table__.c.id.primary_key is True
    assert Person.__table__.c.id.index in {None, False}
    assert Person.__table__.c.deleted_at.index in {None, False}


def test_base_index_cleanup_is_reversible() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision: str | None = "0010_enable_person_search"' in source
    assert "ix_permissions_id" in source
    assert "ix_liturgical_observances_deleted_at" in source
    assert "op.drop_index" in source
    assert "op.create_index" in source
