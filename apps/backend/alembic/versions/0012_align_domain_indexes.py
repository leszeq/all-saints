"""Align domain indexes with the ORM metadata.

Revision ID: 0012_align_domain_indexes
Revises: 0011_align_base_indexes
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_align_domain_indexes"
down_revision: str | None = "0011_align_base_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Index audit actions used by the administration filters."""
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    """Remove the audit-action index."""
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
