"""Add partial indexes for active person search relations and public ordering."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_active_search_indexes"
down_revision: str | None = "0025_all_souls_observance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_ROWS = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    """Index only active relation rows used by the public search query."""
    op.create_index(
        "ix_persons_public_canonical_name",
        "persons",
        ["canonical_name", "id"],
        postgresql_where=sa.text("status = 'published' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_person_translations_person_id_active",
        "person_translations",
        ["person_id"],
        postgresql_where=ACTIVE_ROWS,
    )
    op.create_index(
        "ix_person_names_person_id_active",
        "person_names",
        ["person_id"],
        postgresql_where=ACTIVE_ROWS,
    )
    op.create_index(
        "ix_person_names_normalized_value_active",
        "person_names",
        ["normalized_value"],
        postgresql_where=ACTIVE_ROWS,
    )
    op.create_index(
        "ix_person_names_value_trgm_active",
        "person_names",
        ["value"],
        postgresql_using="gin",
        postgresql_ops={"value": "gin_trgm_ops"},
        postgresql_where=ACTIVE_ROWS,
    )
    op.create_index(
        "ix_patronages_person_id_active",
        "patronages",
        ["person_id"],
        postgresql_where=ACTIVE_ROWS,
    )
    for column in ("name_pl", "name_en", "description"):
        op.create_index(
            f"ix_patronages_{column}_trgm_active",
            "patronages",
            [column],
            postgresql_using="gin",
            postgresql_ops={column: "gin_trgm_ops"},
            postgresql_where=ACTIVE_ROWS,
        )
    op.create_index(
        "ix_patronages_type_trgm",
        "patronages",
        ["patronage_type"],
        postgresql_using="gin",
        postgresql_ops={"patronage_type": "gin_trgm_ops"},
        postgresql_where=ACTIVE_ROWS,
    )


def downgrade() -> None:
    """Remove the active-only search indexes while preserving existing indexes."""
    op.drop_index("ix_patronages_type_trgm", table_name="patronages")
    for column in ("description", "name_en", "name_pl"):
        op.drop_index(f"ix_patronages_{column}_trgm_active", table_name="patronages")
    op.drop_index("ix_patronages_person_id_active", table_name="patronages")
    op.drop_index("ix_person_names_value_trgm_active", table_name="person_names")
    op.drop_index("ix_person_names_normalized_value_active", table_name="person_names")
    op.drop_index("ix_person_names_person_id_active", table_name="person_names")
    op.drop_index("ix_person_translations_person_id_active", table_name="person_translations")
    op.drop_index("ix_persons_public_canonical_name", table_name="persons")
