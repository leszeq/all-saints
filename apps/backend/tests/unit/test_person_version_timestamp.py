"""Regression coverage for timezone-aware person version timestamps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime

from alembic.config import Config
from alembic.script import ScriptDirectory
from src.domain.hagiography.models import PersonVersion
from src.presentation.api.v1.persons.schemas import PersonVersionSchema

MIGRATION = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "0014_person_version_changed_at.py"
)


def test_changed_at_column_is_timezone_aware() -> None:
    column_type = PersonVersion.__table__.c.changed_at.type

    assert isinstance(column_type, DateTime)
    assert column_type.timezone is True


def test_person_version_schema_exposes_a_datetime() -> None:
    changed_at = datetime.now(UTC)
    payload = PersonVersionSchema.model_validate(
        {
            "id": uuid.uuid4(),
            "person_id": uuid.uuid4(),
            "version_number": 2,
            "snapshot": {"version": 2},
            "changed_at": changed_at.isoformat(),
        }
    )

    assert payload.changed_at == changed_at


def test_timestamp_migration_is_in_the_single_validating_history() -> None:
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    source = MIGRATION.read_text(encoding="utf-8")

    migration = scripts.get_revision("0014_person_version_changed_at")
    successor = scripts.get_revision("0015_drop_legacy_embedding")
    assert migration is not None
    assert successor is not None
    assert successor.down_revision == migration.revision
    assert len(scripts.get_heads()) == 1
    assert 'down_revision: str | None = "0013_refine_editorial_rbac"' in source
    assert "changed_at::timestamptz" in source
    assert "invalid_datetime_format" in source
    assert 'postgresql_using="changed_at::text"' in source
