"""Add permissions for reviewable patronage concepts.

Revision ID: 0023_taxonomy_rbac
Revises: 0022_patronage_concepts
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_taxonomy_rbac"
down_revision: str | None = "0022_patronage_concepts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _grant(role_name: str, action: str) -> None:
    op.execute(
        sa.text(
            """
        INSERT INTO role_permissions (role_id, permission_id, granted_at)
        SELECT roles.id, permissions.id, now()
        FROM roles
        JOIN permissions
          ON permissions.resource = 'taxonomy'
         AND permissions.action = :action
        WHERE roles.name = :role_name
          AND roles.deleted_at IS NULL
          AND permissions.deleted_at IS NULL
          ON CONFLICT (role_id, permission_id) DO NOTHING
        """
        ).bindparams(role_name=role_name, action=action)
    )


def _revoke(role_name: str, action: str) -> None:
    op.execute(
        sa.text(
            """
        DELETE FROM role_permissions assignment
        USING roles, permissions
        WHERE assignment.role_id = roles.id
          AND assignment.permission_id = permissions.id
          AND roles.name = :role_name
          AND permissions.resource = 'taxonomy'
          AND permissions.action = :action
        """
        ).bindparams(role_name=role_name, action=action)
    )


def upgrade() -> None:
    """Install concept dictionary permissions and default role grants."""
    op.execute(
        """
        INSERT INTO permissions (resource, action, description)
        VALUES
          ('taxonomy', 'read', 'Przeglądanie słowników pojęć'),
          ('taxonomy', 'create', 'Tworzenie pojęć i aliasów'),
          ('taxonomy', 'update', 'Edycja pojęć i przypisań'),
          ('taxonomy', 'submit', 'Przekazywanie pojęć do recenzji'),
          ('taxonomy', 'review', 'Akceptowanie lub odrzucanie pojęć')
        ON CONFLICT (resource, action) DO UPDATE
        SET description = EXCLUDED.description,
            deleted_at = NULL
        """
    )

    for role_name, action in (
        *(('super_admin', action) for action in ('read', 'create', 'update', 'submit', 'review')),
        *(('admin', action) for action in ('read', 'create', 'update', 'submit', 'review')),
        *(('editor', action) for action in ('read', 'create', 'update', 'submit')),
        ('reviewer', 'read'),
        ('reviewer', 'review'),
        ('translator', 'read'),
        ('reader', 'read'),
    ):
        _grant(role_name, action)


def downgrade() -> None:
    """Remove concept permissions and grants."""
    for role_name, action in (
        *(('super_admin', action) for action in ('read', 'create', 'update', 'submit', 'review')),
        *(('admin', action) for action in ('read', 'create', 'update', 'submit', 'review')),
        *(('editor', action) for action in ('read', 'create', 'update', 'submit')),
        ('reviewer', 'read'),
        ('reviewer', 'review'),
        ('translator', 'read'),
        ('reader', 'read'),
    ):
        _revoke(role_name, action)
    op.execute("DELETE FROM permissions WHERE resource = 'taxonomy'")
