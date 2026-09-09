"""Refresh-token rotation and logout endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.audit_service import AuditContext, add_audit_log
from src.core.config import settings
from src.core.security import JWTService, jwt_service
from src.domain.identity.models import AuditAction, RefreshToken, User, UserRole
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.schemas import TokenResponse

router = APIRouter()


def auth_audit_context(
    request: Request,
    *,
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
) -> AuditContext:
    """Build audit metadata for both identified and rejected sessions."""
    return AuditContext(
        user_id=user_id,
        user_email=user_email,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        request_id=getattr(request.state, "request_id", None),
    )


def set_refresh_cookie(response: Response, raw_token: str) -> None:
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
    set_refresh_cookie(response, raw_refresh_token)

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
                context=auth_audit_context(request, user_id=stored_token.user_id),
                action=AuditAction.LOGOUT,
                resource_type="authentication",
                resource_id=stored_token.user_id,
            )
            await db.flush()

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
