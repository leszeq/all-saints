"""Keep historical public person slugs as permanent redirects."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0019_person_slug_redirects"
down_revision: str | None = "0018_person_translation_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the historical person-slug redirect table."""
    op.create_table(
        "person_slug_redirects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("old_slug", sa.String(length=600), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("old_slug", name="uq_person_slug_redirect_old_slug"),
        comment="Historical public slugs kept for permanent redirects",
    )
    op.create_index(
        "ix_person_slug_redirects_person_id",
        "person_slug_redirects",
        ["person_id"],
    )


def downgrade() -> None:
    """Drop historical public person-slug redirects."""
    op.drop_index("ix_person_slug_redirects_person_id", table_name="person_slug_redirects")
    op.drop_table("person_slug_redirects")
