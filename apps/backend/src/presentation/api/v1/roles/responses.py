"""Response mapping for managed roles."""

from src.domain.identity.models import Role
from src.presentation.api.v1.users.schemas import RoleSchema


def serialize_role(role: Role, user_count: int = 0) -> RoleSchema:
    """Map a role and eager-loaded permissions to its API projection."""
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
