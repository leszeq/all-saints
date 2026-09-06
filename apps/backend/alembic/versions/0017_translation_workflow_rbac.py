"""Add deletion and review visibility for editorial translations.

Revision ID: 0017_translation_workflow_rbac
Revises: 0016_person_names
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017_translation_workflow_rbac"
down_revision: str | None = "0016_person_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _grant(role_name: str, resource: str, action: str) -> None:
    op.execute(
        f"""
        INSERT INTO role_permissions (role_id, permission_id, granted_at)
        SELECT roles.id, permissions.id, now()
        FROM roles
        JOIN permissions
          ON permissions.resource = '{resource}'
         AND permissions.action = '{action}'
        WHERE roles.name = '{role_name}'
          AND roles.deleted_at IS NULL
          AND permissions.deleted_at IS NULL
        ON CONFLICT (role_id, permission_id) DO NOTHING
        """
    )


def _revoke(role_name: str, resource: str, action: str) -> None:
    op.execute(
        f"""
        DELETE FROM role_permissions assignment
        USING roles, permissions
        WHERE assignment.role_id = roles.id
          AND assignment.permission_id = permissions.id
          AND roles.name = '{role_name}'
          AND permissions.resource = '{resource}'
          AND permissions.action = '{action}'
        """
    )


def upgrade() -> None:
    """Install translation deletion and read-only review access."""
    op.execute(
        """
        INSERT INTO permissions (resource, action, description)
        VALUES ('translations', 'delete', 'Usuwanie tłumaczeń')
        ON CONFLICT (resource, action) DO UPDATE
        SET description = EXCLUDED.description,
            deleted_at = NULL
        """
    )

    for role_name, resource, action in (
        ("super_admin", "translations", "delete"),
        ("admin", "translations", "delete"),
        ("translator", "translations", "delete"),
        ("editor", "translations", "read"),
        ("reviewer", "translations", "read"),
        ("reader", "translations", "read"),
    ):
        _grant(role_name, resource, action)


def downgrade() -> None:
    """Remove permissions introduced by this migration."""
    for role_name, resource, action in (
        ("super_admin", "translations", "delete"),
        ("admin", "translations", "delete"),
        ("translator", "translations", "delete"),
        ("editor", "translations", "read"),
        ("reviewer", "translations", "read"),
        ("reader", "translations", "read"),
    ):
        _revoke(role_name, resource, action)

    op.execute(
        """
        DELETE FROM permissions
        WHERE resource = 'translations' AND action = 'delete'
        """
    )
