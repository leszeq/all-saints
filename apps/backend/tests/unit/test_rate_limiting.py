"""Regression tests for Redis-backed login rate limiting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from src.infrastructure.cache.redis_client import RateLimiter
from src.presentation.api.v1.auth.login import _enforce_login_rate_limit
from src.presentation.api.v1.auth.schemas import LoginRequest


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [],
            "client": ("192.0.2.10", 43120),
        }
    )


@pytest.mark.asyncio
async def test_rate_limiter_uses_one_atomic_redis_script() -> None:
    redis = MagicMock()
    redis.eval = AsyncMock(return_value=[3, 42])

    result = await RateLimiter(redis).check(
        identifier="login:ip:192.0.2.10",
        limit=5,
        window_seconds=60,
    )

    assert result.allowed is True
    assert result.remaining == 2
    assert result.retry_after == 42
    redis.eval.assert_awaited_once()
    assert redis.eval.await_args.args[1] == 1
    assert redis.eval.await_args.args[2].startswith("saints:ratelimit:")


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429_with_retry_after() -> None:
    redis = MagicMock()
    redis.eval = AsyncMock(side_effect=[[1, 0], [999, 17]])

    with pytest.raises(HTTPException) as exc_info:
        await _enforce_login_rate_limit(
            credentials=LoginRequest(
                email="editor@example.org",
                password="SecretPassword123!",
            ),
            request=make_request(),
            response=Response(),
            redis=redis,
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "17"}
    keys = [call.args[2] for call in redis.eval.await_args_list]
    assert len(keys) == 2
    assert all("editor@example.org" not in key for key in keys)


@pytest.mark.asyncio
async def test_login_rate_limit_fails_open_when_redis_is_unavailable() -> None:
    redis = MagicMock()
    redis.eval = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

    await _enforce_login_rate_limit(
        credentials=LoginRequest(
            email="editor@example.org",
            password="SecretPassword123!",
        ),
        request=make_request(),
        response=Response(),
        redis=redis,
    )
