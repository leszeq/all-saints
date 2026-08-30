"""Regression coverage for the editorial RBAC matrix."""

from src.domain.identity.models import SystemRole
from src.domain.identity.rbac import (
    ALL_PERMISSION_KEYS,
    PROTECTED_MANAGEMENT_RESOURCES,
    ROLE_PERMISSIONS,
)


def test_super_admin_is_the_only_role_with_identity_management_permissions() -> None:
    assert ROLE_PERMISSIONS[SystemRole.SUPER_ADMIN] == ALL_PERMISSION_KEYS

    for role, permissions in ROLE_PERMISSIONS.items():
        if role == SystemRole.SUPER_ADMIN:
            continue
        assert not {
            permission
            for permission in permissions
            if permission.split(":", maxsplit=1)[0] in PROTECTED_MANAGEMENT_RESOURCES
        }


def test_admin_can_manage_content_but_not_users_or_roles() -> None:
    permissions = ROLE_PERMISSIONS[SystemRole.ADMIN]

    assert {"persons:create", "persons:update", "persons:submit", "persons:review"} <= permissions
    assert "persons:publish" in permissions
    assert "users:read" not in permissions
    assert "roles:read" not in permissions


def test_editor_can_submit_but_cannot_review_or_publish() -> None:
    permissions = ROLE_PERMISSIONS[SystemRole.EDITOR]

    assert {"persons:read", "persons:create", "persons:update", "persons:submit"} <= permissions
    assert "persons:review" not in permissions
    assert "persons:publish" not in permissions


def test_reviewer_can_decide_but_cannot_edit_content() -> None:
    permissions = ROLE_PERMISSIONS[SystemRole.REVIEWER]

    assert {"persons:read", "persons:review"} <= permissions
    assert "persons:create" not in permissions
    assert "persons:update" not in permissions
    assert "persons:submit" not in permissions
    assert "persons:publish" not in permissions
