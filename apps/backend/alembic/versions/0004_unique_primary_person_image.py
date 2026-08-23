"""Ensure that a person has at most one active primary image.

Revision ID: 0004_unique_primary_person_image
Revises: 0003_add_person_embeddings
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0004_unique_primary_person_image"
down_revision: str | None = "0003_add_person_embeddings"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Deduplicate primary images and enforce one active avatar per person."""
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY person_id
                    ORDER BY sort_order ASC, created_at ASC, id ASC
                ) AS position
            FROM images
            WHERE person_id IS NOT NULL
              AND is_primary = true
              AND deleted_at IS NULL
        )
        UPDATE images
        SET is_primary = false,
            updated_at = now()
        WHERE id IN (SELECT id FROM ranked WHERE position > 1)
        """
    )
    op.create_index(
        "uq_images_active_primary_person",
        "images",
        ["person_id"],
        unique=True,
        postgresql_where=sa.text(
            "person_id IS NOT NULL AND is_primary = true AND deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    """Remove the single-primary-image constraint."""
    op.drop_index("uq_images_active_primary_person", table_name="images")
