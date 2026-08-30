"""Refine editorial RBAC and enforce a single superadministrator.

Revision ID: 0013_refine_editorial_rbac
Revises: 0012_align_domain_indexes
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_refine_editorial_rbac"
down_revision: str | None = "0012_align_domain_indexes"
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


def upgrade() -> None:
    """Install action-specific workflow permissions and tighten identity access."""
    op.execute(
        """
        INSERT INTO permissions (resource, action, description)
        VALUES
          ('persons', 'submit', 'Przekazywanie szkiców do recenzji'),
          ('persons', 'review', 'Akceptowanie lub zwracanie recenzji')
        ON CONFLICT (resource, action) DO UPDATE
        SET description = EXCLUDED.description,
            deleted_at = NULL
        """
    )

    for role_name, permission in (
        ("super_admin", ("persons", "submit")),
        ("super_admin", ("persons", "review")),
        ("admin", ("persons", "submit")),
        ("admin", ("persons", "review")),
        ("editor", ("persons", "submit")),
        ("reviewer", ("persons", "review")),
    ):
        _grant(role_name, *permission)

    op.execute(
        """
        DELETE FROM role_permissions assignment
        USING roles, permissions
        WHERE assignment.role_id = roles.id
          AND assignment.permission_id = permissions.id
          AND roles.name <> 'super_admin'
          AND permissions.resource IN ('users', 'roles')
        """
    )
    op.execute(
        """
        DELETE FROM role_permissions assignment
        USING roles, permissions
        WHERE assignment.role_id = roles.id
          AND assignment.permission_id = permissions.id
          AND roles.name = 'reviewer'
          AND permissions.resource = 'persons'
          AND permissions.action = 'update'
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_single_super_admin()
        RETURNS trigger AS $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM roles
            WHERE id = NEW.role_id AND name = 'super_admin'
          ) THEN
            PERFORM pg_advisory_xact_lock(hashtext('all_saints_single_super_admin'));
            IF EXISTS (
              SELECT 1
              FROM user_roles assignment
              JOIN roles ON roles.id = assignment.role_id
              JOIN users ON users.id = assignment.user_id
              WHERE roles.name = 'super_admin'
                AND users.deleted_at IS NULL
                AND assignment.user_id <> NEW.user_id
            ) THEN
              RAISE EXCEPTION 'Only one active superadministrator is allowed'
                USING ERRCODE = '23505';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_single_super_admin
        BEFORE INSERT OR UPDATE OF role_id, user_id ON user_roles
        FOR EACH ROW EXECUTE FUNCTION enforce_single_super_admin()
        """
    )


def downgrade() -> None:
    """Restore the former broad reviewer/admin policy."""
    op.execute("DROP TRIGGER IF EXISTS trg_single_super_admin ON user_roles")
    op.execute("DROP FUNCTION IF EXISTS enforce_single_super_admin()")

    _grant("admin", "users", "read")
    _grant("reviewer", "persons", "update")

    op.execute(
        """
        DELETE FROM permissions
        WHERE resource = 'persons' AND action IN ('submit', 'review')
        """
    )
