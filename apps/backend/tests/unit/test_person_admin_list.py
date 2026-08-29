"""Regression tests for protected person-list audit metadata."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.person_service import PersonService
from src.main import app
from src.presentation.api.v1.persons.schemas import PersonAdminListItemSchema


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
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    restored = await PersonService(db).restore_person(person_id, user_id=editor_id)

    version = db.add.call_args.args[0]
    assert restored is person
    assert person.deleted_at is None
    assert person.version == 3
    assert version.changed_by_id == editor_id
    assert version.change_summary == "Przywrócenie rekordu"


def test_editor_identity_is_exposed_only_by_protected_admin_contract() -> None:
    schema = app.openapi()
    public_properties = schema["components"]["schemas"]["PersonListItemSchema"]["properties"]
    admin_properties = schema["components"]["schemas"]["PersonAdminListItemSchema"]["properties"]
    admin_operation = schema["paths"]["/api/v1/persons/admin"]["get"]

    assert "last_modified_by" not in public_properties
    assert "last_modified_by" in admin_properties
    assert admin_operation["security"] == [{"HTTPBearer": []}]
