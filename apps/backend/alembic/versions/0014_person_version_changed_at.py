"""Store person version timestamps as timezone-aware datetimes.

Revision ID: 0014_person_version_changed_at
Revises: 0013_refine_editorial_rbac
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014_person_version_changed_at"
down_revision: str | None = "0013_refine_editorial_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Validate existing text values before converting them to TIMESTAMPTZ."""
    op.execute(
        """
        DO $$
        BEGIN
          PERFORM changed_at::timestamptz
          FROM person_versions
          WHERE changed_at IS NOT NULL;
        EXCEPTION
          WHEN invalid_datetime_format OR datetime_field_overflow THEN
            RAISE EXCEPTION
              'person_versions.changed_at contains a value that cannot be converted to timestamptz';
        END
        $$
        """
    )
    op.alter_column(
        "person_versions",
        "changed_at",
        existing_type=sa.String(length=50),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="changed_at::timestamptz",
    )


def downgrade() -> None:
    """Convert timestamps back to their PostgreSQL ISO text representation."""
    op.alter_column(
        "person_versions",
        "changed_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using="changed_at::text",
    )
