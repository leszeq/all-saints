"""Integration coverage for the authentication session lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import AuditContext
from src.application.services.auth_session_service import (
    AuthenticationSessionService,
    InactiveSessionAccountError,
)
from src.core.security import jwt_service, password_hasher
from src.domain.identity.models import AuditAction, AuditLog, RefreshToken, User, UserStatus


def _user(email: str, *, status: UserStatus = UserStatus.ACTIVE) -> User:
    return User(
        email=email,
        hashed_password=password_hasher.hash("CorrectPassword123!"),
        full_name="Testowy użytkownik sesji",
        status=status,
        is_verified=True,
    )


def _refresh_token(user: User) -> tuple[str, RefreshToken]:
    raw_token, token_hash = jwt_service.create_refresh_token()
    return raw_token, RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


@pytest.mark.asyncio
async def test_rotate_replaces_active_refresh_token_without_committing(
    db_session: AsyncSession,
) -> None:
    user = _user("session-rotation@example.com")
    db_session.add(user)
    await db_session.flush()
    raw_token, stored_token = _refresh_token(user)
    db_session.add(stored_token)
    await db_session.commit()

    rotated = await AuthenticationSessionService(db_session).rotate(
        raw_token,
        user_agent="pytest",
        ip_address="127.0.0.1",
    )

    tokens = list(
        (
            await db_session.scalars(
                select(RefreshToken)
                .where(RefreshToken.user_id == user.id)
                .order_by(RefreshToken.created_at)
            )
        ).all()
    )
    assert rotated.access_token
    assert rotated.refresh_token != raw_token
    assert len(tokens) == 2
    assert tokens[0].revoked_at is not None
    assert tokens[1].revoked_at is None
    assert tokens[1].token_hash == jwt_service.hash_refresh_token(rotated.refresh_token)
    assert tokens[1].user_agent == "pytest"


@pytest.mark.asyncio
async def test_rotate_does_not_consume_token_for_inactive_account(
    db_session: AsyncSession,
) -> None:
    user = _user("inactive-session@example.com", status=UserStatus.INACTIVE)
    db_session.add(user)
    await db_session.flush()
    raw_token, stored_token = _refresh_token(user)
    db_session.add(stored_token)
    await db_session.commit()

    with pytest.raises(InactiveSessionAccountError):
        await AuthenticationSessionService(db_session).rotate(raw_token)

    await db_session.refresh(stored_token)
    assert stored_token.revoked_at is None


@pytest.mark.asyncio
async def test_revoke_records_logout_and_ignores_unknown_token(
    db_session: AsyncSession,
) -> None:
    user = _user("session-logout@example.com")
    db_session.add(user)
    await db_session.flush()
    raw_token, stored_token = _refresh_token(user)
    db_session.add(stored_token)
    await db_session.commit()
    service = AuthenticationSessionService(db_session)

    revoked = await service.revoke(
        raw_token,
        audit_context=AuditContext(
            user_email=user.email,
            request_id="session-request",
        ),
    )
    unknown_revoked = await service.revoke(
        "unknown-refresh-token",
        audit_context=AuditContext(request_id="unknown-request"),
    )

    audit_log = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.user_id == user.id,
                AuditLog.action == AuditAction.LOGOUT.value,
            )
        )
    ).scalar_one()
    assert revoked is True
    assert unknown_revoked is False
    assert stored_token.revoked_at is not None
    assert audit_log.resource_type == "authentication"
    assert audit_log.request_id == "session-request"


@pytest.mark.asyncio
async def test_revoke_all_for_user_preserves_already_revoked_timestamp(
    db_session: AsyncSession,
) -> None:
    user = _user("session-password-change@example.com")
    db_session.add(user)
    await db_session.flush()
    _, active_token = _refresh_token(user)
    _, already_revoked = _refresh_token(user)
    previous_revocation = datetime.now(UTC) - timedelta(days=1)
    already_revoked.revoked_at = previous_revocation
    db_session.add_all([active_token, already_revoked])
    await db_session.commit()
    changed_at = datetime.now(UTC)

    await AuthenticationSessionService(db_session).revoke_all_for_user(
        user.id,
        revoked_at=changed_at,
    )
    await db_session.refresh(active_token)
    await db_session.refresh(already_revoked)

    assert active_token.revoked_at == changed_at
    assert already_revoked.revoked_at == previous_revocation
