"""Backwards-compatible facade for user and role administration."""

from src.application.services.access_control_errors import (
    AccessControlConflictError,
    AccessControlNotFoundError,
    AccessControlValidationError,
)
from src.application.services.role_access_control_service import RoleAccessControlService
from src.application.services.user_access_control_service import UserAccessControlService


class AccessControlService(UserAccessControlService, RoleAccessControlService):
    """Expose the legacy combined interface while vertical services stay independent."""


__all__ = [
    "AccessControlConflictError",
    "AccessControlNotFoundError",
    "AccessControlService",
    "AccessControlValidationError",
    "RoleAccessControlService",
    "UserAccessControlService",
]
