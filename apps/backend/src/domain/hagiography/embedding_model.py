"""
PersonEmbedding domain model.

Stores pgvector embeddings for persons to enable semantic search
and related saints recommendations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.base import Base

if TYPE_CHECKING:
    from src.domain.hagiography.models import Person

VECTOR_DIM = 1536


class PersonEmbedding(Base):
    """
    Vector embedding for a hagiographic person.

    Used for:
    - Semantic search (cosine similarity against a query vector)
    - Related saints recommendation (nearest neighbours)
    - Duplicate detection (near-identical vectors)

    The embedding is generated from a combined text document consisting of:
    name, biography, patronages, tags, categories, and occupations.
    """

    __tablename__ = "person_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # The pgvector column – 1536 dimensions (OpenAI text-embedding-3-small)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(VECTOR_DIM),  # type: ignore[arg-type]
        nullable=False,
        comment="1536-dimensional embedding vector for cosine similarity search",
    )

    # The source text used to generate the embedding (for inspection/debugging)
    source_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Text document that was embedded",
    )

    # Which AI provider generated this embedding
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="disabled",
        server_default=text("'disabled'"),
        comment="Embedding provider: openai or ollama",
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="text-embedding-3-small",
        server_default=text("'text-embedding-3-small'"),
        comment="Model name used for generation",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    person: Mapped[Person] = relationship(
        "Person",
        back_populates="embedding",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<PersonEmbedding person_id={self.person_id} provider={self.provider}>"
