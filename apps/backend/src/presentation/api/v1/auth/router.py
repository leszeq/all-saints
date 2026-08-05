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

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from loguru import logger
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.security import JWTService, PasswordHasher, is_strong_password, jwt_service, password_hasher
from src.domain.identity.models import RefreshToken, User, UserStatus
from src.infrastructure.db.session import get_db_session

router = APIRouter()


# ==============================================================================
# SCHEMAS
# ==============================================================================


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, description="Password")


class TokenResponse(BaseModel):
    """Successful authentication response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token TTL in seconds")


class UserProfileResponse(BaseModel):
    """Current user profile."""

    id: str
    email: str
    full_name: str
    status: str
    roles: list[str]
    preferred_language: str
    last_login_at: datetime | None

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Password change request."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


# ==============================================================================
# DEPENDENCIES
# ==============================================================================


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    FastAPI dependency: extract and validate the Bearer token,
    then load the current user from the database.

    Raises:
        HTTPException 401: If token is missing, invalid, or expired.
        HTTPException 403: If user is inactive or locked.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Wymagane uwierzytelnienie",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract token from Authorization header
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise credentials_exception

    # Verify token
    from jose import JWTError
    try:
        payload = jwt_service.verify_access_token(token)
    except JWTError:
        raise credentials_exception

    # Load user
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(UserRole.role).selectinload(Role.permissions))
        .where(User.id == payload.user_id)
        .where(User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

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

    return user


async def require_permission(resource: str, action: str):
    """
    Factory for permission-checking dependencies.

    Usage::

        @router.post("/persons")
        async def create_person(
            user: User = Depends(require_permission("persons", "create")),
        ):
            ...
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Brak uprawnień: {resource}:{action}",
            )
        return user
    return _check


# Fix imports for type checker
from src.domain.identity.models import UserRole, Role  # noqa: E402


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
) -> TokenResponse:
    """
    Authenticate a user and issue tokens.

    The access token is returned in the response body.
    The refresh token is set as an HttpOnly cookie.
    """
    # Load user by email
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.roles)
            .selectinload(UserRole.role)
            .selectinload(Role.permissions)
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
        raise auth_error

    # Check account status
    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto zostało zablokowane",
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zbyt wiele nieudanych prób logowania. Spróbuj za chwilę.",
        )

    # Verify password
    if not password_hasher.verify(credentials.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 10:
            from datetime import timedelta
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            logger.warning(f"Account locked: {user.email} (too many failed attempts)")
        await db.commit()
        raise auth_error

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)

    # Collect role names
    role_names = [ur.role.name for ur in user.roles if ur.role]

    # Issue access token
    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
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
    await db.commit()

    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )

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
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Issue a new access token using the refresh token cookie."""
    from src.core.security import JWTService

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
            selectinload(RefreshToken.user)
            .selectinload(User.roles)
            .selectinload(UserRole.role)
        )
        .where(RefreshToken.token_hash == token_hash)
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

    role_names = [ur.role.name for ur in user.roles if ur.role]

    access_token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=role_names,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Revoke the refresh token and clear the cookie.",
)
async def logout(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Revoke the refresh token and clear the cookie."""
    if refresh_token:
        from src.core.security import JWTService
        token_hash = JWTService.hash_refresh_token(refresh_token)

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one_or_none()

        if stored_token:
            stored_token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user",
    description="Return the profile of the currently authenticated user.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return the current user's profile."""
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        roles=[ur.role.name for ur in current_user.roles if ur.role],
        preferred_language=current_user.preferred_language,
        last_login_at=current_user.last_login_at,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change the current user's password.",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Change the password of the currently authenticated user."""
    # Verify current password
    if not password_hasher.verify(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowe obecne hasło",
        )

    # Validate new password strength
    is_strong, errors = is_strong_password(data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Hasło jest zbyt słabe", "errors": errors},
        )

    # Update password
    current_user.hashed_password = password_hasher.hash(data.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Password changed for user: {current_user.email}")


# Fix import for settings in cookie
from src.core.config import settings  # noqa: E402
