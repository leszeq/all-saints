"""Remove redundant indexes inherited from the original base mixins.

Revision ID: 0011_align_base_indexes
Revises: 0010_enable_person_search
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_align_base_indexes"
down_revision: str | None = "0010_enable_person_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REDUNDANT_PRIMARY_KEY_INDEXES = (
    ("permissions", "ix_permissions_id"),
    ("roles", "ix_roles_id"),
    ("users", "ix_users_id"),
    ("liturgical_observances", "ix_liturgical_observances_id"),
)


def upgrade() -> None:
    """Drop indexes duplicated by each table's primary-key index."""
    for table_name, index_name in REDUNDANT_PRIMARY_KEY_INDEXES:
        op.drop_index(index_name, table_name=table_name)
    op.drop_index(
        "ix_liturgical_observances_deleted_at",
        table_name="liturgical_observances",
    )


def downgrade() -> None:
    """Restore the legacy indexes exactly as they existed before this cleanup."""
    op.create_index(
        "ix_liturgical_observances_deleted_at",
        "liturgical_observances",
        ["deleted_at"],
    )
    for table_name, index_name in reversed(REDUNDANT_PRIMARY_KEY_INDEXES):
        op.create_index(index_name, table_name, ["id"])
