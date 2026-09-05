"""Transaction-boundary coverage for reference-data APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.security import jwt_service
from src.domain.geography.models import Country
from src.domain.hagiography.models import Category, Pope
from src.domain.identity.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)
from src.infrastructure.db.session import get_db_session
from src.main import app


async def _create_reference_editor(db: AsyncSession) -> dict[str, str]:
    role = Role(
        name="reference-transaction-editor",
        display_name="Redaktor danych referencyjnych",
    )
    db.add(role)
    await db.flush()
    for resource in ("geography", "persons"):
        permission = Permission(
            resource=resource,
            action="create",
            description=f"{resource}:create",
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

    user = User(
        email="reference-transaction@example.com",
        hashed_password="not-used-by-token-tests",
        full_name="Redaktor Danych Referencyjnych",
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
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_reference_data_waits_for_request_unit_of_work(
    test_engine,
    db_session: AsyncSession,
) -> None:
    headers = await _create_reference_editor(db_session)
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as writer_session, session_factory() as observer_session:

        async def override_get_db_without_commit():
            yield writer_session

        app.dependency_overrides[get_db_session] = override_get_db_without_commit
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
            ) as client:
                country_response = await client.post(
                    "/api/v1/geography/countries",
                    headers=headers,
                    json={"name_pl": "Testlandia", "name_en": "Testland"},
                )
                category_response = await client.post(
                    "/api/v1/taxonomy/categories",
                    headers=headers,
                    json={"name_pl": "Testowa kategoria", "name_en": "Test category"},
                )
                pope_response = await client.post(
                    "/api/v1/popes",
                    headers=headers,
                    json={"papal_name": "Testowy Papież"},
                )
        finally:
            app.dependency_overrides.clear()

        assert country_response.status_code == 201
        assert category_response.status_code == 201
        assert pope_response.status_code == 201
        country_id = uuid.UUID(country_response.json()["id"])
        category_id = uuid.UUID(category_response.json()["id"])
        pope_id = uuid.UUID(pope_response.json()["id"])

        assert (
            await observer_session.execute(select(Country).where(Country.id == country_id))
        ).scalar_one_or_none() is None
        assert (
            await observer_session.execute(select(Category).where(Category.id == category_id))
        ).scalar_one_or_none() is None
        assert (
            await observer_session.execute(select(Pope).where(Pope.id == pope_id))
        ).scalar_one_or_none() is None

        await writer_session.commit()

        assert (
            await observer_session.execute(select(Country).where(Country.id == country_id))
        ).scalar_one().name_pl == "Testlandia"
        assert (
            await observer_session.execute(select(Category).where(Category.id == category_id))
        ).scalar_one().slug == "testowa-kategoria"
        assert (
            await observer_session.execute(select(Pope).where(Pope.id == pope_id))
        ).scalar_one().papal_name == "Testowy Papież"
