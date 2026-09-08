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
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.auth_security_service import AuthenticationSecurityRecorder
from src.core.config import settings
from src.core.security import JWTService, jwt_service, password_hasher
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
    "require_permission",
    "update_me",
]


def _audit_context(
    request: Request,
    *,
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
) -> AuditContext:
    return AuditContext(
        user_id=user_id,
        user_email=user_email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        request_id=getattr(request.state, "request_id", None),
    )


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Set the refresh cookie consistently for login and token rotation."""
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )


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
            context=_audit_context(request, user_email=credentials.email.lower()),
            reason="invalid_credentials",
        )
        raise auth_error

    # Check account status
    if user.status == UserStatus.BANNED:
        await security_recorder.record_login_failure(
            context=_audit_context(request, user_id=user.id, user_email=user.email),
            reason="account_banned",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto zostało zablokowane",
        )

    if user.is_locked:
        await security_recorder.record_login_failure(
            context=_audit_context(request, user_id=user.id, user_email=user.email),
            reason="account_locked",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zbyt wiele nieudanych prób logowania. Spróbuj za chwilę.",
        )

    # Verify password
    if not password_hasher.verify(credentials.password, user.hashed_password):
        account_locked = await security_recorder.record_login_failure(
            context=_audit_context(request, user_id=user.id, user_email=user.email),
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
        context=_audit_context(request, user_id=user.id, user_email=user.email),
        action=AuditAction.LOGIN,
        resource_type="authentication",
        resource_id=user.id,
    )
    await db.flush()

    # Set refresh token as HttpOnly cookie
    _set_refresh_cookie(response, raw_refresh_token)

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Use the refresh token cookie to obtain a new access token.",
    responses={
        200: {"description": "Token refreshed"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Issue a new access token using the refresh token cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak tokenu odświeżającego",
        )

    token_hash = JWTService.hash_refresh_token(refresh_token)

    # Load and validate stored refresh token
    result = await db.execute(
        select(RefreshToken)
        .options(
            selectinload(RefreshToken.user).selectinload(User.roles).selectinload(UserRole.role)
        )
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None or not stored_token.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token odświeżający jest nieważny lub wygasł",
        )

    user = stored_token.user
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest nieaktywne",
        )
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest tymczasowo zablokowane",
        )

    role_names = [ur.role.name for ur in user.roles if ur.role]

    raw_refresh_token, new_token_hash = jwt_service.create_refresh_token()
    stored_token.revoked_at = datetime.now(UTC)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=jwt_service.get_token_expiry("refresh"),
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.flush()

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
        password_changed_at=user.password_changed_at,
    )
    _set_refresh_cookie(response, raw_refresh_token)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Logout",
    description="Revoke the refresh token and clear the cookie.",
)
async def logout(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Revoke the refresh token and clear the cookie."""
    if refresh_token:
        token_hash = JWTService.hash_refresh_token(refresh_token)

        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        stored_token = result.scalar_one_or_none()

        if stored_token:
            stored_token.revoked_at = datetime.now(UTC)
            add_audit_log(
                db,
                context=_audit_context(request, user_id=stored_token.user_id),
                action=AuditAction.LOGOUT,
                resource_type="authentication",
                resource_id=stored_token.user_id,
            )
            await db.flush()

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")


router.include_router(account_router)
