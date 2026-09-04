"""Regression tests for protected person-list audit metadata."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.person_service import PersonService
from src.domain.hagiography.models import PersonVersion
from src.domain.identity.models import AuditAction, AuditLog
from src.main import app
from src.presentation.api.v1.persons.schemas import PersonAdminListItemSchema


def _empty_snapshot_query_result() -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = None
    return result


def test_admin_person_schema_contains_editor_metadata() -> None:
    now = datetime.now(UTC)
    editor = SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Redaktor Testowy",
        avatar_url=None,
    )
    item = PersonAdminListItemSchema.model_validate(
        {
            "id": uuid.uuid4(),
            "slug": "sw-testowy",
            "canonical_name": "Św. Testowy",
            "person_type": "saint",
            "status": "draft",
            "gender": "unknown",
            "is_featured": False,
            "created_at": now,
            "updated_at": now,
            "last_modified_at": now,
            "last_modified_by": editor,
        }
    )

    assert item.last_modified_by is not None
    assert item.last_modified_by.full_name == "Redaktor Testowy"


@pytest.mark.asyncio
async def test_get_last_editors_maps_latest_users() -> None:
    person_id = uuid.uuid4()
    editor = SimpleNamespace(id=uuid.uuid4(), full_name="Redaktor")
    result = MagicMock()
    result.all.return_value = [(person_id, editor)]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    editors = await PersonService(db).get_last_editors([person_id])

    assert editors[person_id] is editor


@pytest.mark.asyncio
async def test_restore_records_the_responsible_editor() -> None:
    person_id = uuid.uuid4()
    editor_id = uuid.uuid4()
    person = SimpleNamespace(
        id=person_id,
        deleted_at=datetime.now(UTC),
        version=2,
        updated_at=datetime.now(UTC),
        orders=[],
        to_dict=lambda: {"id": str(person_id), "version": 3},
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = person
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[result, *[_empty_snapshot_query_result() for _ in range(12)]]
    )
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    restored = await PersonService(db).restore_person(person_id, user_id=editor_id)

    version = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], PersonVersion)
    )
    audit_log = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], AuditLog)
    )
    assert restored is person
    assert person.deleted_at is None
    assert person.version == 3
    assert version.changed_by_id == editor_id
    assert version.change_summary == "Przywrócenie rekordu"
    assert audit_log.action == AuditAction.RESTORE.value
    assert audit_log.user_id == editor_id


@pytest.mark.asyncio
async def test_soft_delete_stages_an_audit_record_before_commit() -> None:
    person_id = uuid.uuid4()
    editor_id = uuid.uuid4()
    person = SimpleNamespace(
        id=person_id,
        deleted_at=None,
        version=1,
        updated_at=datetime.now(UTC),
        to_dict=lambda: {
            "id": str(person_id),
            "deleted_at": person.deleted_at.isoformat() if person.deleted_at else None,
            "version": person.version,
        },
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=_empty_snapshot_query_result())
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    await PersonService(db).soft_delete_person(person, user_id=editor_id)

    version = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], PersonVersion)
    )
    audit_log = next(
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], AuditLog)
    )
    assert audit_log.action == AuditAction.DELETE.value
    assert audit_log.user_id == editor_id
    assert audit_log.old_value["deleted_at"] is None
    assert audit_log.new_value["deleted_at"] is not None
    assert version.changed_by_id == editor_id
    assert version.change_summary == "Usunięcie rekordu"
    db.commit.assert_awaited_once()


def test_editor_identity_is_exposed_only_by_protected_admin_contract() -> None:
    schema = app.openapi()
    public_properties = schema["components"]["schemas"]["PersonListItemSchema"]["properties"]
    admin_properties = schema["components"]["schemas"]["PersonAdminListItemSchema"]["properties"]
    admin_operation = schema["paths"]["/api/v1/persons/admin"]["get"]

    assert "last_modified_by" not in public_properties
    assert "last_modified_by" in admin_properties
    assert admin_operation["security"] == [{"HTTPBearer": []}]
