"""Integration coverage for source-relation versioning through the HTTP API."""

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
from src.domain.sources.models import Bibliography


async def _source_editor(db: AsyncSession) -> tuple[User, dict[str, str]]:
    role = Role(name="source-version-editor", display_name="Redaktor źródeł")
    db.add(role)
    await db.flush()
    for resource, action in (
        ("sources", "create"),
        ("sources", "delete"),
        ("images", "create"),
    ):
        permission = Permission(resource=resource, action=action)
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
        email="source-version@example.com",
        hashed_password="not-used-by-token-tests",
        full_name="Redaktor Źródeł",
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


@pytest.mark.asyncio
async def test_adding_and_removing_source_creates_person_versions(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user, headers = await _source_editor(db_session)
    person = Person(
        slug="sw-zrodlo-wersjonowane",
        canonical_name="Św. Źródło Wersjonowane",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
        version=1,
    )
    bibliography = Bibliography(title="Wersjonowane źródło")
    db_session.add_all([person, bibliography])
    await db_session.commit()

    create_response = await async_client.post(
        f"/api/v1/sources/person-links/{person.id}",
        headers=headers,
        json={
            "bibliography_id": str(bibliography.id),
            "page_reference": "s. 42",
            "is_primary": True,
        },
    )

    assert create_response.status_code == 201
    link_id = create_response.json()["id"]
    await db_session.refresh(person)
    assert person.version == 2
    created_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 2,
            )
        )
    ).scalar_one()
    assert created_version.changed_by_id == user.id
    assert created_version.snapshot["sources"][0]["bibliography_id"] == str(
        bibliography.id
    )

    delete_response = await async_client.delete(
        f"/api/v1/sources/person-links/{person.id}/{link_id}",
        headers=headers,
    )

    assert delete_response.status_code == 204
    await db_session.refresh(person)
    assert person.version == 3
    removed_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 3,
            )
        )
    ).scalar_one()
    assert removed_version.snapshot["sources"] == []

    image_response = await async_client.post(
        "/api/v1/sources/images",
        headers=headers,
        json={
            "person_id": str(person.id),
            "url": "https://example.test/versioned-image.jpg",
            "is_primary": True,
        },
    )

    assert image_response.status_code == 201
    await db_session.refresh(person)
    assert person.version == 4
    image_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == person.id,
                PersonVersion.version_number == 4,
            )
        )
    ).scalar_one()
    assert image_version.snapshot["images"][0]["url"] == (
        "https://example.test/versioned-image.jpg"
    )
    audit_events = list(
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == person.id)
                .order_by(AuditLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [event.extra_metadata["operation"] for event in audit_events] == [
        "add",
        "remove",
        "add",
    ]
