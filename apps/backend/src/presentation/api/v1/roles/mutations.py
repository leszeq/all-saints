"""Protected role-management mutations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlNotFoundError,
    AccessControlValidationError,
)
from src.application.services.role_access_control_service import RoleAccessControlService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.access_control_http import raise_access_error
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.roles.responses import serialize_role
from src.presentation.api.v1.users.schemas import (
    CreateRoleRequest,
    RoleSchema,
    UpdateRoleRequest,
)

router = APIRouter()


async def create_role(
    data: CreateRoleRequest,
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("roles", "create")),
) -> RoleSchema:
    """Create a custom role from assignable content permissions."""
    try:
        role = await RoleAccessControlService(db).create_role(
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            permission_keys=data.permissions,
        )
    except (AccessControlConflictError, AccessControlValidationError) as exc:
        raise_access_error(exc)
    return serialize_role(role)


@router.patch(
    "/{role_id}",
    response_model=RoleSchema,
    summary="Update a custom role",
)
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
        raise_access_error(exc)
    return serialize_role(role)


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
        raise_access_error(exc)
