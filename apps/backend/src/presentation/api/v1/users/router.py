"""Superadministrator-only user account management endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlNotFoundError,
    AccessControlValidationError,
)
from src.application.services.user_access_control_service import UserAccessControlService
from src.domain.identity.models import User, UserStatus
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.users.schemas import (
    CreateUserRequest,
    RoleSummarySchema,
    UpdateUserRequest,
    UserListItemSchema,
    UserListResponseSchema,
)

router = APIRouter()


def _serialize_user(user: User) -> UserListItemSchema:
    roles = sorted(
        (assignment.role for assignment in user.roles if assignment.role is not None),
        key=lambda role: role.display_name,
    )
    primary_role = roles[0] if roles else None
    return UserListItemSchema(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        roles=[role.name for role in roles],
        primary_role=(
            RoleSummarySchema(
                id=primary_role.id,
                name=primary_role.name,
                display_name=primary_role.display_name,
                is_system=primary_role.is_system,
            )
            if primary_role
            else None
        ),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _raise_access_error(exc: ValueError) -> NoReturn:
    if isinstance(exc, AccessControlNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, AccessControlValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=UserListResponseSchema, summary="List managed users")
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(None, max_length=200),
    status_filter: UserStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("users", "read")),
) -> UserListResponseSchema:
    users, total = await UserAccessControlService(db).list_users(
        page=page,
        per_page=per_page,
        search=search,
        status=status_filter,
    )
    return UserListResponseSchema(
        items=[_serialize_user(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )


@router.post(
    "",
    response_model=UserListItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user with one role",
)
async def create_user(
    data: CreateUserRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("users", "create")),
) -> UserListItemSchema:
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
        _raise_access_error(exc)
    return _serialize_user(user)


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
        _raise_access_error(exc)
    return _serialize_user(user)


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
        _raise_access_error(exc)
