"""Add the pointer used by the future public revision projection."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0028_published_revision_pointer"
down_revision: str | None = "0027_publication_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the selected published revision without backfilling legacy rows yet."""
    op.add_column(
        "persons",
        sa.Column("published_revision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_persons_published_revision_id",
        "persons",
        "publication_revisions",
        ["published_revision_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_persons_published_revision_id",
        "persons",
        ["published_revision_id"],
    )


def downgrade() -> None:
    """Remove the published revision pointer and its index."""
    op.drop_index("ix_persons_published_revision_id", table_name="persons")
    op.drop_constraint(
        "fk_persons_published_revision_id",
        "persons",
        type_="foreignkey",
    )
    op.drop_column("persons", "published_revision_id")
