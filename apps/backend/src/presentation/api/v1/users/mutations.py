"""Protected user-management mutations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlNotFoundError,
    AccessControlValidationError,
)
from src.application.services.user_access_control_service import UserAccessControlService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.access_control_http import raise_access_error
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.users.responses import serialize_user
from src.presentation.api.v1.users.schemas import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListItemSchema,
)

router = APIRouter()


async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("users", "create")),
) -> UserListItemSchema:
    """Create a managed user with one assignable role."""
    try:
        user = await UserAccessControlService(db).create_user(
            email=str(data.email),
            password=data.password,
            full_name=data.full_name,
            role_id=data.role_id,
            preferred_language=data.preferred_language,
            actor_id=current_user.id,
        )
    except (AccessControlConflictError, AccessControlValidationError) as exc:
        raise_access_error(exc)
    return serialize_user(user)


@router.patch(
    "/{user_id}",
    response_model=UserListItemSchema,
    summary="Update a managed user",
)
async def update_user(
    user_id: uuid.UUID,
    data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("users", "update")),
) -> UserListItemSchema:
    try:
        user = await UserAccessControlService(db).update_user(
            user_id,
            actor_id=current_user.id,
            full_name=data.full_name,
            status=data.status,
            role_id=data.role_id,
            preferred_language=data.preferred_language,
            bio=data.bio,
        )
    except (AccessControlNotFoundError, AccessControlConflictError) as exc:
        raise_access_error(exc)
    return serialize_user(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Deactivate a managed user",
)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("users", "delete")),
) -> None:
    try:
        await UserAccessControlService(db).delete_user(
            user_id,
            actor_id=current_user.id,
        )
    except (AccessControlNotFoundError, AccessControlConflictError) as exc:
        raise_access_error(exc)
