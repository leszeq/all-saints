"""Response mapping for managed users."""

from src.domain.identity.models import User
from src.presentation.api.v1.users.schemas import (
    RoleSummarySchema,
    UserListItemSchema,
)


def serialize_user(user: User) -> UserListItemSchema:
    """Map a user and eager-loaded role assignments to its API projection."""
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
