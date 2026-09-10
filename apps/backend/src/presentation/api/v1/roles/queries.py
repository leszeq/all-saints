"""Protected role and permission-matrix queries."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.role_access_control_service import RoleAccessControlService
from src.domain.identity.models import User
from src.domain.identity.rbac import CUSTOM_ROLE_PERMISSION_KEYS, PERMISSIONS
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.roles.responses import serialize_role
from src.presentation.api.v1.users.schemas import (
    PermissionSchema,
    RoleListResponseSchema,
)


async def list_roles(
    db: AsyncSession = Depends(get_db_session),
    _super_admin: User = Depends(require_permission("roles", "read")),
) -> RoleListResponseSchema:
    """Return roles together with the assignable permission matrix."""
    roles, user_counts = await RoleAccessControlService(db).list_roles()
    return RoleListResponseSchema(
        items=[serialize_role(role, user_counts.get(role.id, 0)) for role in roles],
        permissions=[
            PermissionSchema(
                key=permission.key,
                resource=permission.resource,
                action=permission.action,
                description=permission.description,
                group=permission.group,
                assignable_to_custom_roles=(permission.key in CUSTOM_ROLE_PERMISSION_KEYS),
            )
            for permission in PERMISSIONS
        ],
    )
