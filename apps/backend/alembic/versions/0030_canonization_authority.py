"""Store the textual authority supplied by portable canonization imports."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_canonization_authority"
down_revision: str | None = "0029_backfill_pub_revision_ptr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add optional free-text authority without changing existing records."""
    op.add_column(
        "canonizations",
        sa.Column("authority", sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    """Remove the optional authority field."""
    op.drop_column("canonizations", "authority")
