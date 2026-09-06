"""Integration coverage for the protected person-translation workflow."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import jwt_service
from src.domain.hagiography.models import (
    Gender,
    Person,
    PersonTranslation,
    PersonType,
    PersonVersion,
    PublicationStatus,
)
from src.domain.identity.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)


async def _translation_user(
    db: AsyncSession,
    *,
    actions: tuple[str, ...] = ("read", "create", "update", "delete"),
    suffix: str = "editor",
) -> tuple[User, dict[str, str]]:
    role = Role(name=f"translation-{suffix}", display_name="Tłumacz testowy")
    db.add(role)
    await db.flush()
    for action in actions:
        permission = Permission(resource="translations", action=action)
        db.add(permission)
        await db.flush()
        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                granted_at=datetime.now(UTC),
            )
        )
    user = User(
        email=f"translation-{suffix}@example.com",
        hashed_password="not-used-by-token-tests",
        full_name="Tłumacz Testowy",
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
    return user, {"Authorization": f"Bearer {token}"}


def _draft_person() -> Person:
    return Person(
        slug="sw-rita-tlumaczenie",
        canonical_name="Św. Rita z Cascii",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.FEMALE.value,
        version=1,
    )


@pytest.mark.asyncio
async def test_translation_lifecycle_versions_parent_and_audits_changes(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user, headers = await _translation_user(db_session)
    person = _draft_person()
    db_session.add(person)
    await db_session.commit()

    create_response = await async_client.post(
        f"/api/v1/persons/{person.id}/translations",
        headers=headers,
        json={
            "language_code": "EN_us",
            "canonical_name": "Saint Rita of Cascia",
            "summary": "Patron saint of impossible causes.",
            "expected_person_version": 1,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["language_code"] == "en-us"
    assert created["version"] == 1
    assert created["person_version"] == 2
    translation_id = created["id"]

    list_response = await async_client.get(
        f"/api/v1/persons/{person.id}/translations",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert list_response.json()["person_version"] == 2
    assert [item["id"] for item in list_response.json()["items"]] == [translation_id]

    update_response = await async_client.patch(
        f"/api/v1/persons/{person.id}/translations/en-US",
        headers=headers,
        json={
            "summary": "Patron saint of impossible and difficult causes.",
            "expected_person_version": 2,
            "expected_version": 1,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["version"] == 2
    assert update_response.json()["person_version"] == 3

    delete_response = await async_client.delete(
        f"/api/v1/persons/{person.id}/translations/en_us",
        headers=headers,
        params={"expected_person_version": 3, "expected_version": 2},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "language_code": "en-us",
        "person_version": 4,
    }

    restore_response = await async_client.post(
        f"/api/v1/persons/{person.id}/translations",
        headers=headers,
        json={
            "language_code": "en-US",
            "canonical_name": "Saint Rita of Cascia",
            "expected_person_version": 4,
        },
    )
    assert restore_response.status_code == 201
    assert restore_response.json()["id"] == translation_id
    assert restore_response.json()["version"] == 4
    assert restore_response.json()["person_version"] == 5

    await db_session.refresh(person)
    translation = (
        await db_session.execute(
            select(PersonTranslation).where(PersonTranslation.id == translation_id)
        )
    ).scalar_one()
    latest_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 5,
            )
        )
    ).scalar_one()
    audit_rows = list(
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == person.id, AuditLog.user_id == user.id)
                .order_by(AuditLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    assert person.version == 5
    assert translation.deleted_at is None
    assert latest_version.snapshot["_snapshot_schema_version"] == 2
    assert latest_version.snapshot["translations"][0]["language_code"] == "en-us"
    assert [row.extra_metadata["operation"] for row in audit_rows] == [
        "create",
        "update",
        "delete",
        "restore",
    ]


@pytest.mark.asyncio
async def test_translation_mutation_requires_draft_and_current_versions(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, headers = await _translation_user(db_session, suffix="state")
    person = _draft_person()
    db_session.add(person)
    await db_session.commit()

    stale_response = await async_client.post(
        f"/api/v1/persons/{person.id}/translations",
        headers=headers,
        json={
            "language_code": "en",
            "canonical_name": "Saint Rita",
            "expected_person_version": 99,
        },
    )
    assert stale_response.status_code == 409
    assert stale_response.json()["detail"]["code"] == "person_version_conflict"

    person.status = PublicationStatus.REVIEW.value
    await db_session.commit()
    review_response = await async_client.post(
        f"/api/v1/persons/{person.id}/translations",
        headers=headers,
        json={
            "language_code": "en",
            "canonical_name": "Saint Rita",
            "expected_person_version": 1,
        },
    )
    assert review_response.status_code == 409
    assert review_response.json()["detail"]["code"] == "translation_parent_not_draft"


@pytest.mark.asyncio
async def test_translation_write_requires_specific_permission(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, headers = await _translation_user(db_session, actions=("read",), suffix="reader")
    person = _draft_person()
    db_session.add(person)
    await db_session.commit()

    response = await async_client.post(
        f"/api/v1/persons/{person.id}/translations",
        headers=headers,
        json={
            "language_code": "en",
            "canonical_name": "Saint Rita",
            "expected_person_version": 1,
        },
    )

    assert response.status_code == 403
