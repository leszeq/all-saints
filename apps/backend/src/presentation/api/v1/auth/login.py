"""Credential authentication, login throttling and token issuance."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.auth_login_service import (
    AuthenticationLoginService,
    BannedLoginAccountError,
    InvalidLoginCredentialsError,
    LockedLoginAccountError,
)
from src.application.services.auth_security_service import AuthenticationSecurityRecorder
from src.core.config import settings
from src.infrastructure.cache.redis_client import RateLimiter, RedisClient, get_redis
from src.infrastructure.db.session import get_db_session, get_session_factory
from src.presentation.api.v1.auth.schemas import LoginRequest, TokenResponse
from src.presentation.api.v1.auth.sessions import auth_audit_context, set_refresh_cookie

router = APIRouter()


def get_authentication_security_recorder() -> AuthenticationSecurityRecorder:
    """Provide the isolated writer used for durable login-denial events."""
    return AuthenticationSecurityRecorder(get_session_factory())


async def _enforce_login_rate_limit(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    redis: RedisClient,
) -> None:
    """Limit login attempts per source address and normalized account."""
    client_ip = request.client.host if request.client else "unknown"
    account_digest = hashlib.sha256(credentials.email.lower().encode()).hexdigest()
    checks = (
        ("ip", f"login:ip:{client_ip}", settings.RATE_LIMIT_LOGIN_IP),
        ("account", f"login:account:{account_digest}", settings.RATE_LIMIT_LOGIN_ACCOUNT),
    )
    limiter = RateLimiter(redis)
    remaining: list[int] = []

    try:
        for scope, identifier, limit in checks:
            result = await limiter.check(
                identifier=identifier,
                limit=limit,
                window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
            )
            remaining.append(result.remaining)
            if not result.allowed:
                logger.warning("Login rate limit exceeded for scope={scope}", scope=scope)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Zbyt wiele prób logowania. Spróbuj ponownie później.",
                    headers={"Retry-After": str(result.retry_after)},
                )
    except HTTPException:
        raise
    except Exception as exc:
        # Authentication remains available during a Redis incident. The
        # persistent per-account lockout remains the second line of defence.
        logger.error(
            "Login rate limiting unavailable: {error_type}",
            error_type=type(exc).__name__,
        )
        return

    response.headers["X-RateLimit-Remaining"] = str(min(remaining))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description=(
        "Authenticate with email and password. Returns a JWT access token and "
        "sets a refresh token cookie."
    ),
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account inactive or locked"},
        429: {"description": "Too many login attempts"},
    },
)
async def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: RedisClient = Depends(get_redis),
    security_recorder: AuthenticationSecurityRecorder = Depends(
        get_authentication_security_recorder
    ),
) -> TokenResponse:
    """Authenticate a user, record the attempt and issue both token types."""
    await _enforce_login_rate_limit(credentials, request, response, redis)

    try:
        session = await AuthenticationLoginService(
            db,
            security_recorder=security_recorder,
        ).authenticate(
            email=credentials.email,
            password=credentials.password,
            audit_context=auth_audit_context(request),
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    except InvalidLoginCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
        ) from exc
    except BannedLoginAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto zostało zablokowane",
        ) from exc
    except LockedLoginAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zbyt wiele nieudanych prób logowania. Spróbuj za chwilę.",
        ) from exc

    set_refresh_cookie(response, session.refresh_token)
    return TokenResponse(
        access_token=session.access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
