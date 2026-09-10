"""Superadministrator-only role and permission matrix endpoints."""

from __future__ import annotations

import uuid
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlNotFoundError,
    AccessControlValidationError,
)
from src.application.services.role_access_control_service import RoleAccessControlService
from src.domain.identity.models import Role, User
from src.domain.identity.rbac import CUSTOM_ROLE_PERMISSION_KEYS, PERMISSIONS
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.users.schemas import (
    CreateRoleRequest,
    PermissionSchema,
    RoleListResponseSchema,
    RoleSchema,
    UpdateRoleRequest,
)

router = APIRouter()


def _serialize_role(role: Role, user_count: int = 0) -> RoleSchema:
    permission_keys = sorted(
        f"{assignment.permission.resource}:{assignment.permission.action}"
        for assignment in role.permissions
        if assignment.permission is not None
    )
    return RoleSchema(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
        user_count=user_count,
        permissions=permission_keys,
        created_at=role.created_at,
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


@router.get("", response_model=RoleListResponseSchema, summary="Get roles and permission matrix")
async def list_roles(
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("roles", "read")),
) -> RoleListResponseSchema:
    roles, user_counts = await RoleAccessControlService(db).list_roles()
    return RoleListResponseSchema(
        items=[_serialize_role(role, user_counts.get(role.id, 0)) for role in roles],
        permissions=[
            PermissionSchema(
                key=permission.key,
                resource=permission.resource,
                action=permission.action,
                description=permission.description,
                group=permission.group,
                assignable_to_custom_roles=permission.key in CUSTOM_ROLE_PERMISSION_KEYS,
            )
            for permission in PERMISSIONS
        ],
    )


@router.post(
    "",
    response_model=RoleSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role",
)
async def create_role(
    data: CreateRoleRequest,
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("roles", "create")),
) -> RoleSchema:
    try:
        role = await RoleAccessControlService(db).create_role(
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            permission_keys=data.permissions,
        )
    except (AccessControlConflictError, AccessControlValidationError) as exc:
        _raise_access_error(exc)
    return _serialize_role(role)


@router.patch("/{role_id}", response_model=RoleSchema, summary="Update a custom role")
async def update_role(
    role_id: uuid.UUID,
    data: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("roles", "update")),
) -> RoleSchema:
    try:
        role = await RoleAccessControlService(db).update_role(
            role_id,
            display_name=data.display_name,
            description=data.description,
            permission_keys=data.permissions,
        )
    except (
        AccessControlNotFoundError,
        AccessControlConflictError,
        AccessControlValidationError,
    ) as exc:
        _raise_access_error(exc)
    return _serialize_role(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Delete an unused custom role",
)
async def delete_role(
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("roles", "delete")),
) -> None:
    try:
        await RoleAccessControlService(db).delete_role(role_id)
    except (AccessControlNotFoundError, AccessControlConflictError) as exc:
        _raise_access_error(exc)
