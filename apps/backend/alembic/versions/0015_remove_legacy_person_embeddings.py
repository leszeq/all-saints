"""Remove the unused JSONB person embedding column.

Revision ID: 0015_drop_legacy_embedding
Revises: 0014_person_version_changed_at
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_drop_legacy_embedding"
down_revision: str | None = "0014_person_version_changed_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the legacy column only when no unpublished vector data remains."""
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM persons WHERE embedding_vector IS NOT NULL
          ) THEN
            RAISE EXCEPTION
              'persons.embedding_vector still contains data; migrate it before dropping the column';
          END IF;
        END
        $$
        """
    )
    op.drop_column("persons", "embedding_vector")


def downgrade() -> None:
    """Restore the nullable compatibility column without making it authoritative."""
    op.add_column(
        "persons",
        sa.Column(
            "embedding_vector",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Legacy compatibility field; PersonEmbedding remains authoritative",
        ),
    )
