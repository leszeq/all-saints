"""Transaction and durability coverage for authentication writes."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.services.auth_security_service import AuthenticationSecurityRecorder
from src.core.security import password_hasher
from src.domain.identity.models import AuditAction, AuditLog, RefreshToken, User, UserStatus
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.db.session import get_db_session
from src.main import app
from src.presentation.api.v1.auth import login as auth_login
from src.presentation.api.v1.auth.router import get_authentication_security_recorder


def _active_user(email: str, *, failed_attempts: int = 0) -> User:
    return User(
        email=email,
        hashed_password=password_hasher.hash("CorrectPassword123!"),
        full_name="Testowy Redaktor",
        status=UserStatus.ACTIVE,
        is_verified=True,
        failed_login_attempts=failed_attempts,
    )


@pytest.mark.asyncio
async def test_successful_login_waits_for_request_unit_of_work(
    test_engine,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _active_user("auth-success-transaction@example.com")
    db_session.add(user)
    await db_session.commit()
    user_id = user.id
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    monkeypatch.setattr(auth_login, "_enforce_login_rate_limit", AsyncMock())

    async with session_factory() as writer_session, session_factory() as observer_session:

        async def override_get_db_without_commit():
            yield writer_session

        async def override_redis():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_without_commit
        app.dependency_overrides[get_redis] = override_redis
        app.dependency_overrides[get_authentication_security_recorder] = lambda: (
            AuthenticationSecurityRecorder(session_factory)
        )
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": user.email,
                        "password": "CorrectPassword123!",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert "refresh_token=" in response.headers["set-cookie"]
        observed_user = (
            await observer_session.execute(select(User).where(User.id == user_id))
        ).scalar_one()
        assert observed_user.last_login_at is None
        assert (
            await observer_session.execute(
                select(RefreshToken).where(RefreshToken.user_id == user_id)
            )
        ).scalar_one_or_none() is None
        assert (
            await observer_session.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id,
                    AuditLog.action == AuditAction.LOGIN.value,
                )
            )
        ).scalar_one_or_none() is None

        await writer_session.commit()
        await observer_session.refresh(observed_user)
        stored_token = (
            await observer_session.execute(
                select(RefreshToken).where(RefreshToken.user_id == user_id)
            )
        ).scalar_one()
        login_audit = (
            await observer_session.execute(
                select(AuditLog).where(
                    AuditLog.user_id == user_id,
                    AuditLog.action == AuditAction.LOGIN.value,
                )
            )
        ).scalar_one()
        assert observed_user.last_login_at is not None
        assert stored_token.revoked_at is None
        assert login_audit.resource_type == "authentication"


@pytest.mark.asyncio
async def test_failed_login_counter_and_audit_survive_request_rollback(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _active_user("auth-failure-transaction@example.com", failed_attempts=9)
    db_session.add(user)
    await db_session.commit()
    monkeypatch.setattr(auth_login, "_enforce_login_rate_limit", AsyncMock())

    response = await async_client.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    await db_session.refresh(user)
    failure_audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action == AuditAction.LOGIN_FAILED.value,
            )
        )
    ).scalar_one()
    assert user.failed_login_attempts == 10
    assert user.locked_until is not None
    assert failure_audit.extra_metadata == {"reason": "invalid_credentials"}
