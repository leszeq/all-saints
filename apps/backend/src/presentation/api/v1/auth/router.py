"""
Authentication API endpoints.

Endpoints:
- POST /auth/login         – Login with email/password
- POST /auth/refresh       – Refresh access token
- POST /auth/logout        – Revoke refresh token
- GET  /auth/me            – Get current user profile
- POST /auth/change-password – Change own password
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.audit_service import add_audit_log
from src.application.services.auth_security_service import AuthenticationSecurityRecorder
from src.core.config import settings
from src.core.security import jwt_service, password_hasher
from src.domain.identity.models import (
    AuditAction,
    RefreshToken,
    Role,
    User,
    UserRole,
    UserStatus,
)
from src.infrastructure.cache.redis_client import RateLimiter, RedisClient, get_redis
from src.infrastructure.db.session import get_db_session, get_session_factory
from src.presentation.api.v1.auth.account import (
    change_password,
    get_me,
    update_me,
)
from src.presentation.api.v1.auth.account import (
    router as account_router,
)
from src.presentation.api.v1.auth.dependencies import get_current_user, require_permission
from src.presentation.api.v1.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from src.presentation.api.v1.auth.sessions import (
    auth_audit_context,
    logout,
    refresh_token,
    set_refresh_cookie,
)
from src.presentation.api.v1.auth.sessions import router as sessions_router

router = APIRouter()

__all__ = [
    "ChangePasswordRequest",
    "LoginRequest",
    "TokenResponse",
    "UpdateProfileRequest",
    "UserProfileResponse",
    "change_password",
    "get_current_user",
    "get_me",
    "logout",
    "refresh_token",
    "require_permission",
    "update_me",
]


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
        # Authentication must remain available during a Redis incident. The
        # persistent per-account lockout below remains the second line of defence.
        logger.error(
            "Login rate limiting unavailable: {error_type}",
            error_type=type(exc).__name__,
        )
        return

    response.headers["X-RateLimit-Remaining"] = str(min(remaining))


# ==============================================================================
# ENDPOINTS
# ==============================================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns a JWT access token and sets a refresh token cookie.",
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
    """
    Authenticate a user and issue tokens.

    The access token is returned in the response body.
    The refresh token is set as an HttpOnly cookie.
    """
    await _enforce_login_rate_limit(credentials, request, response, redis)

    # Load user by email
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions)
        )
        .where(User.email == credentials.email.lower())
        .where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    # Generic error to prevent user enumeration
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nieprawidłowy email lub hasło",
    )

    if user is None:
        await security_recorder.record_login_failure(
            context=auth_audit_context(request, user_email=credentials.email.lower()),
            reason="invalid_credentials",
        )
        raise auth_error

    # Check account status
    if user.status == UserStatus.BANNED:
        await security_recorder.record_login_failure(
            context=auth_audit_context(request, user_id=user.id, user_email=user.email),
            reason="account_banned",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto zostało zablokowane",
        )

    if user.is_locked:
        await security_recorder.record_login_failure(
            context=auth_audit_context(request, user_id=user.id, user_email=user.email),
            reason="account_locked",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zbyt wiele nieudanych prób logowania. Spróbuj za chwilę.",
        )

    # Verify password
    if not password_hasher.verify(credentials.password, user.hashed_password):
        account_locked = await security_recorder.record_login_failure(
            context=auth_audit_context(request, user_id=user.id, user_email=user.email),
            reason="invalid_credentials",
            increment_attempts=True,
        )
        if account_locked:
            logger.warning(f"Account locked: {user.email} (too many failed attempts)")
        raise auth_error

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)

    # Collect role names
    role_names = [ur.role.name for ur in user.roles if ur.role]

    # Issue access token
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
        password_changed_at=user.password_changed_at,
    )

    # Issue refresh token
    raw_refresh_token, token_hash = jwt_service.create_refresh_token()
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=jwt_service.get_token_expiry("refresh"),
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    db.add(refresh_token_record)
    add_audit_log(
        db,
        context=auth_audit_context(request, user_id=user.id, user_email=user.email),
        action=AuditAction.LOGIN,
        resource_type="authentication",
        resource_id=user.id,
    )
    await db.flush()

    # Set refresh token as HttpOnly cookie
    set_refresh_cookie(response, raw_refresh_token)

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


router.include_router(sessions_router)
router.include_router(account_router)
