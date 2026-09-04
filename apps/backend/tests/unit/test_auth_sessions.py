"""Regression tests for refresh rotation and password-change session revocation."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from src.core.security import jwt_service, password_hasher
from src.domain.identity.models import RefreshToken
from src.presentation.api.v1.auth.router import (
    ChangePasswordRequest,
    change_password,
    get_current_user,
)
from src.presentation.api.v1.auth.router import (
    refresh_token as refresh_access_token,
)


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/refresh",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
    )


def test_access_token_carries_password_version() -> None:
    changed_at = datetime(2026, 8, 29, 10, 11, 12, 345678, tzinfo=UTC)
    token = jwt_service.create_access_token(
        user_id=uuid4(),
        email="editor@example.org",
        roles=["editor"],
        password_changed_at=changed_at,
    )

    payload = jwt_service.verify_access_token(token)

    assert payload.matches_password_version(changed_at)
    assert not payload.matches_password_version(None)


@pytest.mark.asyncio
async def test_refresh_rotates_the_stored_token_and_cookie() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="editor@example.org",
        roles=[SimpleNamespace(role=SimpleNamespace(name="editor"))],
        is_active=True,
        is_locked=False,
        password_changed_at=None,
    )
    stored_token = SimpleNamespace(is_valid=True, user=user, revoked_at=None)
    result = MagicMock()
    result.scalar_one_or_none.return_value = stored_token
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    response = Response()

    token_response = await refresh_access_token(
        request=make_request(),
        response=response,
        refresh_token="old-raw-refresh-token",
        db=db,
    )

    assert token_response.access_token
    assert stored_token.revoked_at is not None
    assert "FOR UPDATE" in str(db.execute.await_args.args[0])
    new_token = next(
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], RefreshToken)
    )
    assert new_token.token_hash != jwt_service.hash_refresh_token("old-raw-refresh-token")
    assert any(
        header == b"set-cookie" and b"refresh_token=" in value
        for header, value in response.raw_headers
    )


@pytest.mark.asyncio
async def test_password_change_revokes_all_refresh_tokens() -> None:
    old_password = "OldPassword123!"
    user = SimpleNamespace(
        id=uuid4(),
        email="editor@example.org",
        hashed_password=password_hasher.hash(old_password),
        password_changed_at=None,
    )
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    response = Response()

    await change_password(
        data=ChangePasswordRequest(
            current_password=old_password,
            new_password="NewPassword456!",
        ),
        response=response,
        current_user=user,
        db=db,
    )

    assert user.password_changed_at is not None
    assert password_hasher.verify("NewPassword456!", user.hashed_password)
    statement = db.execute.await_args.args[0]
    assert "UPDATE refresh_tokens" in str(statement)
    assert "revoked_at" in str(statement)
    assert any(
        header == b"set-cookie" and b"Max-Age=0" in value
        for header, value in response.raw_headers
    )


@pytest.mark.asyncio
async def test_access_token_is_rejected_after_password_change() -> None:
    user_id = uuid4()
    token = jwt_service.create_access_token(
        user_id=user_id,
        email="editor@example.org",
        roles=["editor"],
    )
    user = SimpleNamespace(
        id=user_id,
        password_changed_at=datetime.now(UTC),
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            request=make_request(),
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token,
            ),
            db=db,
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_request_is_enriched_with_user_context() -> None:
    user_id = uuid4()
    token = jwt_service.create_access_token(
        user_id=user_id,
        email="editor@example.org",
        roles=["editor"],
    )
    user = SimpleNamespace(
        id=user_id,
        email="editor@example.org",
        password_changed_at=None,
        is_active=True,
        is_locked=False,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    request = make_request()

    authenticated = await get_current_user(
        request=request,
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        db=db,
    )

    assert authenticated is user
    assert request.state.user_id == str(user_id)
    assert request.state.user_email == "editor@example.org"
