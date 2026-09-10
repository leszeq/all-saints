"""User-management API composition and backwards-compatible exports."""

from fastapi import APIRouter, status

from src.presentation.api.v1.access_control_http import raise_access_error
from src.presentation.api.v1.users.mutations import (
    create_user,
    delete_user,
    update_user,
)
from src.presentation.api.v1.users.mutations import router as mutations_router
from src.presentation.api.v1.users.queries import list_users
from src.presentation.api.v1.users.responses import serialize_user
from src.presentation.api.v1.users.schemas import (
    CreateUserRequest,
    RoleSummarySchema,
    UpdateUserRequest,
    UserListItemSchema,
    UserListResponseSchema,
)

router = APIRouter()

_raise_access_error = raise_access_error
_serialize_user = serialize_user

__all__ = [
    "CreateUserRequest",
    "RoleSummarySchema",
    "UpdateUserRequest",
    "UserListItemSchema",
    "UserListResponseSchema",
    "create_user",
    "delete_user",
    "list_users",
    "raise_access_error",
    "serialize_user",
    "update_user",
]

router.add_api_route(
    "",
    list_users,
    methods=["GET"],
    response_model=UserListResponseSchema,
    summary="List managed users",
)
router.add_api_route(
    "",
    create_user,
    methods=["POST"],
    response_model=UserListItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user with one role",
)
router.include_router(mutations_router)
