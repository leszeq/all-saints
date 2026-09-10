"""Authentication API composition and backwards-compatible exports."""

from __future__ import annotations

from fastapi import APIRouter

from src.presentation.api.v1.auth.account import (
    change_password,
    get_me,
    update_me,
)
from src.presentation.api.v1.auth.account import (
    router as account_router,
)
from src.presentation.api.v1.auth.dependencies import get_current_user, require_permission
from src.presentation.api.v1.auth.login import (
    _enforce_login_rate_limit,
    get_authentication_security_recorder,
    login,
)
from src.presentation.api.v1.auth.login import router as login_router
from src.presentation.api.v1.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from src.presentation.api.v1.auth.sessions import logout, refresh_token
from src.presentation.api.v1.auth.sessions import router as sessions_router

router = APIRouter()

__all__ = [
    "ChangePasswordRequest",
    "LoginRequest",
    "TokenResponse",
    "UpdateProfileRequest",
    "UserProfileResponse",
    "_enforce_login_rate_limit",
    "change_password",
    "get_authentication_security_recorder",
    "get_current_user",
    "get_me",
    "login",
    "logout",
    "refresh_token",
    "require_permission",
    "update_me",
]

router.include_router(login_router)
router.include_router(sessions_router)
router.include_router(account_router)
