"""Endpoints for the currently authenticated user's own account."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.audit_service import add_audit_log
from src.core.config import settings
from src.core.security import is_strong_password, password_hasher
from src.domain.identity.models import AuditAction, RefreshToken, User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.dependencies import get_current_user
from src.presentation.api.v1.auth.schemas import (
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserProfileResponse,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


def _profile_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        roles=[user_role.role.name for user_role in user.roles if user_role.role],
        permissions=sorted(user.get_permissions()),
        preferred_language=user.preferred_language,
        last_login_at=user.last_login_at,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user",
    description="Return the profile of the currently authenticated user.",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    """Return the current user's profile."""
    return _profile_response(current_user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
    description="Update editable profile fields for the currently authenticated user.",
)
async def update_me(
    data: UpdateProfileRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """Update the current user's own profile."""
    previous_profile = {
        "full_name": current_user.full_name,
        "preferred_language": current_user.preferred_language,
    }
    if data.full_name is not None:
        current_user.full_name = data.full_name.strip()
    if data.preferred_language is not None:
        current_user.preferred_language = data.preferred_language.strip().lower()

    current_user.updated_at = datetime.now(UTC)
    add_audit_log(
        db,
        context=audit_context_from_request(request, current_user),
        action=AuditAction.UPDATE,
        resource_type="users",
        resource_id=current_user.id,
        old_value=previous_profile,
        new_value={
            "full_name": current_user.full_name,
            "preferred_language": current_user.preferred_language,
        },
        extra_metadata={"scope": "own_profile"},
    )
    await db.flush()
    await db.refresh(current_user)

    return _profile_response(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Change password",
    description="Change the current user's password.",
)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Change the password of the currently authenticated user."""
    if not password_hasher.verify(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowe obecne hasło",
        )

    is_strong, errors = is_strong_password(data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Hasło jest zbyt słabe", "errors": errors},
        )

    changed_at = datetime.now(UTC)
    current_user.hashed_password = password_hasher.hash(data.new_password)
    current_user.password_changed_at = changed_at
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=changed_at)
    )
    add_audit_log(
        db,
        context=audit_context_from_request(request, current_user),
        action=AuditAction.UPDATE,
        resource_type="users",
        resource_id=current_user.id,
        extra_metadata={"event": "password_changed", "sessions_revoked": True},
    )
    await db.flush()

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=settings.SECURE_COOKIES,
        httponly=True,
        samesite="lax",
    )

    logger.info(f"Password changed for user: {current_user.email}")
