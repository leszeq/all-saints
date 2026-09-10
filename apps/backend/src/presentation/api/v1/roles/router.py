"""Role-management API composition and backwards-compatible exports."""

from fastapi import APIRouter, status

from src.presentation.api.v1.access_control_http import raise_access_error
from src.presentation.api.v1.roles.mutations import (
    create_role,
    delete_role,
    update_role,
)
from src.presentation.api.v1.roles.mutations import router as mutations_router
from src.presentation.api.v1.roles.queries import list_roles
from src.presentation.api.v1.roles.responses import serialize_role
from src.presentation.api.v1.users.schemas import (
    CreateRoleRequest,
    PermissionSchema,
    RoleListResponseSchema,
    RoleSchema,
    UpdateRoleRequest,
)

router = APIRouter()

_raise_access_error = raise_access_error
_serialize_role = serialize_role

__all__ = [
    "CreateRoleRequest",
    "PermissionSchema",
    "RoleListResponseSchema",
    "RoleSchema",
    "UpdateRoleRequest",
    "create_role",
    "delete_role",
    "list_roles",
    "raise_access_error",
    "serialize_role",
    "update_role",
]

router.add_api_route(
    "",
    list_roles,
    methods=["GET"],
    response_model=RoleListResponseSchema,
    summary="Get roles and permission matrix",
)
router.add_api_route(
    "",
    create_role,
    methods=["POST"],
    response_model=RoleSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom role",
)
router.include_router(mutations_router)
