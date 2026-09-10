"""Refresh-token rotation and logout endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import AuditContext
from src.application.services.auth_session_service import (
    AuthenticationSessionService,
    InactiveSessionAccountError,
    InvalidRefreshTokenError,
    LockedSessionAccountError,
)
from src.core.config import settings
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

    service = AuthenticationSessionService(db)
    try:
        rotated_session = await service.rotate(
            refresh_token,
            user_agent=request.headers.get("User-Agent"),
            ip_address=request.client.host if request.client else None,
        )
    except InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token odświeżający jest nieważny lub wygasł",
        ) from exc
    except InactiveSessionAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest nieaktywne",
        ) from exc
    except LockedSessionAccountError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest tymczasowo zablokowane",
        ) from exc

    set_refresh_cookie(response, rotated_session.refresh_token)

    return TokenResponse(
        access_token=rotated_session.access_token,
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
        await AuthenticationSessionService(db).revoke(
            refresh_token,
            audit_context=auth_audit_context(request),
        )

    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
