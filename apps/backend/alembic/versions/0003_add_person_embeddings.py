"""
Add person_embeddings table with pgvector support.

Creates:
- Extension: vector (pgvector)
- Table: person_embeddings with VECTOR(1536) column

Revision ID: 0003_add_person_embeddings
Revises: 0002_seed_person_reference_data
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision: str = "0003_add_person_embeddings"
down_revision: str | None = "0002_seed_person_reference_data"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Create person_embeddings table with pgvector column."""

    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create table
    op.create_table(
        "person_embeddings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False,
        ),
        sa.Column(
            "person_id",
            UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # pgvector column – 1536 dimensions (OpenAI text-embedding-3-small compatible)
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=False,
        ),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False, server_default="disabled"),
        sa.Column(
            "model",
            sa.String(100),
            nullable=False,
            server_default="text-embedding-3-small",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # IVFFlat index for approximate nearest neighbour search using cosine distance.
    # lists=100 is suitable for up to ~1M rows; use ivfflat for datasets < 1M,
    # hnsw for larger datasets (requires pgvector >= 0.5.0).
    # Note: index cannot be created on empty table with IVFFlat – skip for now,
    # will be created after first data is inserted via a separate migration or script.
    # For development purposes we use a simple sequential scan (no index needed < 10k rows).

    # For production with data, run:
    #   CREATE INDEX CONCURRENTLY ON person_embeddings
    #   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


def downgrade() -> None:
    """Drop person_embeddings table."""
    op.drop_table("person_embeddings")
    # Note: we do NOT drop the vector extension as other tables might use it
