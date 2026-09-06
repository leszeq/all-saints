"""Integration coverage for user, role, and permission administration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.services.access_control_service import AccessControlService
from src.core.security import jwt_service
from src.domain.identity.models import (
    Permission,
    Role,
    RolePermission,
    SystemRole,
    User,
    UserRole,
    UserStatus,
)
from src.domain.identity.rbac import ROLE_PERMISSIONS


async def _create_role(
    db: AsyncSession,
    role_name: SystemRole,
) -> Role:
    role = Role(
        name=role_name.value,
        display_name=role_name.value,
        is_system=True,
    )
    db.add(role)
    await db.flush()

    for key in ROLE_PERMISSIONS[role_name]:
        resource, action = key.split(":", maxsplit=1)
        permission = (
            await db.execute(
                select(Permission).where(
                    Permission.resource == resource,
                    Permission.action == action,
                )
            )
        ).scalar_one_or_none()
        if permission is None:
            permission = Permission(
                resource=resource,
                action=action,
                description=key,
            )
            db.add(permission)
            await db.flush()
        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                granted_at=datetime.now(UTC),
            )
        )
    return role


async def _create_actor(
    db: AsyncSession,
    role_name: SystemRole,
    email: str,
) -> tuple[User, Role, dict[str, str]]:
    role = await _create_role(db, role_name)
    user = User(
        email=email,
        hashed_password="not-used-by-token-tests",
        full_name=email,
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    db.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
            assigned_at=datetime.now(UTC),
            assigned_by_id=None,
        )
    )
    await db.commit()
    token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=[role.name],
    )
    return user, role, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_access_control_service_defers_changes_to_unit_of_work(test_engine) -> None:
    actor_id = uuid.uuid4()
    managed_user_id = uuid.uuid4()
    custom_role_id = uuid.uuid4()
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as setup_session:
        setup_session.add_all(
            [
                User(
                    id=actor_id,
                    email="access-owner@example.com",
                    hashed_password="not-used",
                    full_name="Access Owner",
                    status=UserStatus.ACTIVE,
                    is_verified=True,
                ),
                User(
                    id=managed_user_id,
                    email="access-managed@example.com",
                    hashed_password="not-used",
                    full_name="Before commit",
                    status=UserStatus.ACTIVE,
                    is_verified=True,
                ),
                Role(
                    id=custom_role_id,
                    name="access_transaction_test",
                    display_name="Before commit",
                    is_system=False,
                ),
            ]
        )
        await setup_session.commit()

    async with session_factory() as writer_session, session_factory() as observer_session:
        service = AccessControlService(writer_session)
        await service.update_user(
            managed_user_id,
            actor_id=actor_id,
            full_name="After commit",
        )
        await service.update_role(custom_role_id, display_name="After commit")

        observed_user = (
            await observer_session.execute(select(User).where(User.id == managed_user_id))
        ).scalar_one()
        observed_role = (
            await observer_session.execute(select(Role).where(Role.id == custom_role_id))
        ).scalar_one()
        assert observed_user.full_name == "Before commit"
        assert observed_role.display_name == "Before commit"

        await writer_session.commit()
        await observer_session.refresh(observed_user)
        await observer_session.refresh(observed_role)
        assert observed_user.full_name == "After commit"
        assert observed_role.display_name == "After commit"


@pytest.mark.asyncio
async def test_only_super_admin_can_create_a_user_with_an_assignable_role(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, super_headers = await _create_actor(
        db_session,
        SystemRole.SUPER_ADMIN,
        "owner-access@example.com",
    )
    editor_role = Role(
        name=SystemRole.EDITOR.value,
        display_name="Redaktor",
        is_system=True,
    )
    db_session.add(editor_role)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/users",
        headers=super_headers,
        json={
            "email": "new-editor@example.com",
            "password": "StrongEditor123!",
            "full_name": "Nowy Redaktor",
            "role_id": str(editor_role.id),
        },
    )

    assert response.status_code == 201
    assert response.json()["roles"] == [SystemRole.EDITOR.value]
    assert response.json()["primary_role"]["display_name"] == "Redaktor"


@pytest.mark.asyncio
async def test_admin_cannot_list_or_manage_users(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, admin_headers = await _create_actor(
        db_session,
        SystemRole.ADMIN,
        "content-admin@example.com",
    )

    list_response = await async_client.get("/api/v1/users", headers=admin_headers)
    profile_response = await async_client.get("/api/v1/auth/me", headers=admin_headers)
    create_response = await async_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": "forbidden@example.com",
            "password": "StrongEditor123!",
            "full_name": "Forbidden User",
            "role_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403
    assert "persons:publish" in profile_response.json()["permissions"]
    assert "users:read" not in profile_response.json()["permissions"]


@pytest.mark.asyncio
async def test_super_admin_role_cannot_be_assigned_to_another_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, super_role, super_headers = await _create_actor(
        db_session,
        SystemRole.SUPER_ADMIN,
        "sole-owner@example.com",
    )

    response = await async_client.post(
        "/api/v1/users",
        headers=super_headers,
        json={
            "email": "second-owner@example.com",
            "password": "StrongEditor123!",
            "full_name": "Second Owner",
            "role_id": str(super_role.id),
        },
    )

    assert response.status_code == 409
    assert "superadministrator" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_super_admin_can_update_and_deactivate_a_managed_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, super_headers = await _create_actor(
        db_session,
        SystemRole.SUPER_ADMIN,
        "user-owner@example.com",
    )
    editor_role = await _create_role(db_session, SystemRole.EDITOR)
    reviewer_role = await _create_role(db_session, SystemRole.REVIEWER)
    await db_session.commit()
    created = await async_client.post(
        "/api/v1/users",
        headers=super_headers,
        json={
            "email": "managed@example.com",
            "password": "StrongEditor123!",
            "full_name": "Managed Editor",
            "role_id": str(editor_role.id),
        },
    )
    user_id = created.json()["id"]

    updated = await async_client.patch(
        f"/api/v1/users/{user_id}",
        headers=super_headers,
        json={
            "full_name": "Managed Reviewer",
            "status": "inactive",
            "role_id": str(reviewer_role.id),
        },
    )
    deleted = await async_client.delete(
        f"/api/v1/users/{user_id}",
        headers=super_headers,
    )
    listed = await async_client.get("/api/v1/users", headers=super_headers)

    assert updated.status_code == 200
    assert updated.json()["roles"] == [SystemRole.REVIEWER.value]
    assert updated.json()["status"] == "inactive"
    assert deleted.status_code == 204
    assert all(item["id"] != user_id for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_custom_roles_can_be_created_only_from_content_permissions(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, super_headers = await _create_actor(
        db_session,
        SystemRole.SUPER_ADMIN,
        "role-owner@example.com",
    )

    allowed = await async_client.post(
        "/api/v1/roles",
        headers=super_headers,
        json={
            "name": "source_verifier",
            "display_name": "Weryfikator źródeł",
            "description": "Kontroluje źródła bez dostępu do kont.",
            "permissions": ["persons:read", "sources:read", "sources:update"],
        },
    )
    forbidden = await async_client.post(
        "/api/v1/roles",
        headers=super_headers,
        json={
            "name": "user_manager",
            "display_name": "User manager",
            "permissions": ["users:create"],
        },
    )

    assert allowed.status_code == 201
    assert allowed.json()["permissions"] == [
        "persons:read",
        "sources:read",
        "sources:update",
    ]
    assert forbidden.status_code == 409

    role_id = allowed.json()["id"]
    updated = await async_client.patch(
        f"/api/v1/roles/{role_id}",
        headers=super_headers,
        json={
            "display_name": "Starszy weryfikator źródeł",
            "permissions": ["persons:read", "sources:read"],
        },
    )
    matrix = await async_client.get("/api/v1/roles", headers=super_headers)
    deleted = await async_client.delete(f"/api/v1/roles/{role_id}", headers=super_headers)

    assert updated.status_code == 200
    assert updated.json()["permissions"] == ["persons:read", "sources:read"]
    assert matrix.status_code == 200
    assert any(role["id"] == role_id for role in matrix.json()["items"])
    assert any(
        permission["key"] == "users:create" and permission["assignable_to_custom_roles"] is False
        for permission in matrix.json()["permissions"]
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_editor_and_reviewer_complete_the_full_publication_flow(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, _, editor_headers = await _create_actor(
        db_session,
        SystemRole.EDITOR,
        "workflow-editor@example.com",
    )
    _, _, reviewer_headers = await _create_actor(
        db_session,
        SystemRole.REVIEWER,
        "workflow-reviewer@example.com",
    )

    created = await async_client.post(
        "/api/v1/persons",
        headers=editor_headers,
        json={
            "canonical_name": "Św. Test Pełnego Workflow",
            "person_type": "saint",
            "status": "draft",
            "gender": "unknown",
            "summary_pl": "Zweryfikowane streszczenie testowego rekordu.",
            "biography_pl": "Zweryfikowany biogram testowego rekordu.",
        },
    )
    assert created.status_code == 201
    person_id = created.json()["id"]
    slug = created.json()["slug"]

    submitted = await async_client.post(
        f"/api/v1/editorial/queue/{person_id}/transition",
        headers=editor_headers,
        json={"target_status": "review", "expected_version": 1},
    )
    editor_publish = await async_client.post(
        f"/api/v1/editorial/queue/{person_id}/transition",
        headers=editor_headers,
        json={"target_status": "published", "expected_version": 2},
    )
    reviewer_edit = await async_client.patch(
        f"/api/v1/persons/{person_id}",
        headers=reviewer_headers,
        json={"summary_pl": "Recenzent nie może zmieniać treści."},
    )
    return_without_comment = await async_client.post(
        f"/api/v1/editorial/queue/{person_id}/transition",
        headers=reviewer_headers,
        json={"target_status": "draft", "expected_version": 2},
    )
    returned = await async_client.post(
        f"/api/v1/editorial/queue/{person_id}/transition",
        headers=reviewer_headers,
        json={
            "target_status": "draft",
            "expected_version": 2,
            "note": "Proszę doprecyzować przypis do biogramu.",
        },
    )
    resubmitted = await async_client.post(
        f"/api/v1/editorial/queue/{person_id}/transition",
        headers=editor_headers,
        json={"target_status": "review", "expected_version": 3},
    )
    approved = await async_client.post(
        f"/api/v1/editorial/queue/{person_id}/transition",
        headers=reviewer_headers,
        json={"target_status": "published", "expected_version": 4},
    )
    public_record = await async_client.get(f"/api/v1/persons/{slug}")

    assert submitted.status_code == 200
    assert editor_publish.status_code == 403
    assert reviewer_edit.status_code == 403
    assert return_without_comment.status_code == 409
    assert returned.status_code == 200
    assert resubmitted.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["status"] == "published"
    assert public_record.status_code == 200
