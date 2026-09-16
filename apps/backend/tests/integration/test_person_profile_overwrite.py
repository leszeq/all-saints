"""Overwrite import consent, permissions, stale versions and atomicity."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema
from src.application.person_profile_models import PersonProfileDocument
from src.application.services.audit_service import AuditContext
from src.application.services.person_profile_service import PersonProfileService
from src.application.services.person_service import PersonService
from src.core.security import jwt_service
from src.domain.hagiography.models import Person, PersonVersion
from src.domain.identity.models import AuditLog, Permission, Role, RolePermission, User, UserRole


async def import_user(db: AsyncSession, permissions: set[str]) -> dict[str, str]:
    role = Role(name="profile-importer", display_name="Importer")
    user = User(
        email="profile-importer@example.com",
        full_name="Importer",
        hashed_password="unused",
        status="active",
        is_verified=True,
    )
    db.add_all([role, user])
    await db.flush()
    for key in permissions:
        resource, action = key.split(":")
        permission = Permission(resource=resource, action=action)
        db.add(permission)
        await db.flush()
        db.add(
            RolePermission(
                role_id=role.id, permission_id=permission.id, granted_at=datetime.now(UTC)
            )
        )
    db.add(UserRole(user_id=user.id, role_id=role.id, assigned_at=datetime.now(UTC)))
    await db.commit()
    return {
        "Authorization": f"Bearer {jwt_service.create_access_token(user.id, user.email, [role.name])}"
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,permissions,expected",
    [
        ("draft", {"import:create"}, 403),
        ("draft", {"persons:update"}, 403),
        ("draft", {"import:create", "persons:update"}, 200),
        ("published", {"import:create", "persons:update"}, 403),
        ("published", {"import:create", "persons:update", "persons:publish"}, 200),
    ],
)
async def test_overwrite_api_permissions_and_preserved_status(
    db_session: AsyncSession,
    async_client: AsyncClient,
    status: str,
    permissions: set[str],
    expected: int,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Rita z Cascii",
            summary_pl="Stare streszczenie",
        )
    )
    person.status = status
    person_id, slug, version = str(person.id), person.slug, person.version
    person_count = await db_session.scalar(select(func.count()).select_from(Person))
    headers = await import_user(db_session, permissions)
    document = {
        "profile": {
            "canonical_name": "Św. Rita z Cascii",
            "summary_pl": "Nowa treść",
            "status": "published",
        }
    }
    params = {"overwrite_person_id": person_id, "expected_version": version}
    validation = await async_client.post(
        "/api/v1/persons/import/validate", headers=headers, params=params, json=document
    )
    assert validation.status_code == expected
    if expected == 200:
        assert validation.json()["can_import"]
        assert validation.json()["existing_person"]["id"] == person_id
    result = await async_client.post(
        "/api/v1/persons/import", headers=headers, params=params, json=document
    )
    assert result.status_code == expected
    stored = await db_session.get(Person, uuid.UUID(person_id), populate_existing=True)
    assert stored is not None
    assert stored.status == status
    if expected == 200:
        assert result.json()["id"] == person_id
        assert result.json()["slug"] == slug
        assert stored.summary_pl == "Nowa treść"
        assert stored.version > version
    else:
        assert stored.summary_pl == "Stare streszczenie"
        assert stored.version == version
    assert await db_session.scalar(select(func.count()).select_from(Person)) == person_count


@pytest.mark.asyncio
async def test_overwrite_requires_explicit_matching_target_and_current_version(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Św. Rita z Cascii")
    )
    person_id, version = str(person.id), person.version
    headers = await import_user(db_session, {"import:create", "persons:update"})
    document = {"profile": {"canonical_name": "Św. Rita z Cascii", "summary_pl": "Import"}}
    check = await async_client.post(
        "/api/v1/persons/import/validate", json=document, headers=headers
    )
    assert check.status_code == 200
    assert not check.json()["can_import"]
    assert check.json()["existing_person"]["id"] == person_id
    for params in (
        {},
        {"overwrite_person_id": person_id},
        {"overwrite_person_id": str(uuid.uuid4()), "expected_version": version},
        {"overwrite_person_id": person_id, "expected_version": version + 1},
    ):
        result = await async_client.post(
            "/api/v1/persons/import", json=document, headers=headers, params=params
        )
        assert result.status_code == 409
    params = {"overwrite_person_id": person_id, "expected_version": version}
    saved = await async_client.post(
        "/api/v1/persons/import", json=document, headers=headers, params=params
    )
    assert saved.status_code == 200
    stale = await async_client.post(
        "/api/v1/persons/import", json=document, headers=headers, params=params
    )
    assert stale.status_code == 409


@pytest.mark.asyncio
async def test_overwrite_rollback_restores_profile_versions_and_audit(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(canonical_name="Św. Rita z Cascii", summary_pl="Przed importem")
    )
    person_id, version = person.id, person.version
    await db_session.commit()
    versions = await db_session.scalar(select(func.count()).select_from(PersonVersion))
    audits = await db_session.scalar(select(func.count()).select_from(AuditLog))
    monkeypatch.setattr(
        PersonProfileService,
        "_import_sources",
        AsyncMock(side_effect=RuntimeError("Błąd zapisu relacji")),
    )
    with pytest.raises(RuntimeError, match="Błąd zapisu"):
        async with db_session.begin_nested():
            await PersonProfileService(db_session).import_profile(
                PersonProfileDocument.model_validate(
                    {"profile": {"canonical_name": "Św. Rita z Cascii", "summary_pl": "Nowa treść"}}
                ),
                overwrite_person_id=person_id,
                expected_version=version,
                user_id=None,
                audit_context=AuditContext(),
                granted_permissions={"persons:update"},
            )
    await db_session.refresh(person)
    assert person.summary_pl == "Przed importem"
    assert person.version == version
    assert await db_session.scalar(select(func.count()).select_from(PersonVersion)) == versions
    assert await db_session.scalar(select(func.count()).select_from(AuditLog)) == audits
