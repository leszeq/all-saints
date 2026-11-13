"""Backfill a first published scalar revision for legacy public profiles."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_backfill_published_revision_pointer"
down_revision: str | None = "0028_published_revision_pointer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Keep these statements separately executable so the data migration can be
# verified against a disposable database and rerun safely during deployment
# recovery. A legacy row is eligible only when it has no revision at all; a
# pointer intentionally cleared by a later direct edit is therefore preserved.
BACKFILL_LEGACY_PUBLISHED_REVISIONS_SQL = """
INSERT INTO publication_revisions (
    id,
    person_id,
    revision_number,
    status,
    base_version,
    payload,
    change_summary
)
SELECT
    gen_random_uuid(),
    person.id,
    1,
    'published',
    person.version,
    jsonb_build_object(
        '_snapshot_schema_version', 2,
        '_backfilled_from_live', '0029_backfill_published_revision_pointer',
        'person_type', person.person_type,
        'canonical_name', person.canonical_name,
        'canonical_name_en', person.canonical_name_en,
        'latin_name', person.latin_name,
        'original_name', person.original_name,
        'surnames', person.surnames,
        'religious_name', person.religious_name,
        'epithets', person.epithets,
        'gender', person.gender,
        'era', person.era,
        'century', person.century,
        'birth_date', person.birth_date,
        'birth_year', person.birth_year,
        'death_date', person.death_date,
        'death_year', person.death_year,
        'birth_place_id', person.birth_place_id,
        'death_place_id', person.death_place_id,
        'birth_country_id', person.birth_country_id,
        'death_country_id', person.death_country_id,
        'nationality_id', person.nationality_id,
        'state_of_life_id', person.state_of_life_id,
        'summary_pl', person.summary_pl,
        'biography_pl', person.biography_pl,
        'summary_en', person.summary_en,
        'biography_en', person.biography_en,
        'iconographic_attributes', person.iconographic_attributes,
        'prayers', person.prayers,
        'works', person.works,
        'liturgical_color', person.liturgical_color,
        'is_featured', person.is_featured,
        'external_ids', person.external_ids
    ),
    'Backfill legacy opublikowanego profilu'
FROM persons AS person
WHERE person.status = 'published'
  AND person.deleted_at IS NULL
  AND person.published_revision_id IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM publication_revisions AS existing_revision
      WHERE existing_revision.person_id = person.id
  )
ON CONFLICT (person_id, revision_number) DO NOTHING;
"""

SET_BACKFILLED_POINTERS_SQL = """
UPDATE persons AS person
SET published_revision_id = revision.id,
    updated_at = now()
FROM publication_revisions AS revision
WHERE revision.person_id = person.id
  AND revision.revision_number = 1
  AND revision.status = 'published'
  AND revision.deleted_at IS NULL
  AND revision.payload ->> '_backfilled_from_live' =
      '0029_backfill_published_revision_pointer'
  AND person.status = 'published'
  AND person.deleted_at IS NULL
  AND person.published_revision_id IS NULL
  AND person.version = revision.base_version;
"""


def upgrade() -> None:
    """Seed scalar published revisions without changing existing revision history."""
    op.execute(sa.text(BACKFILL_LEGACY_PUBLISHED_REVISIONS_SQL))
    op.execute(sa.text(SET_BACKFILLED_POINTERS_SQL))


def downgrade() -> None:
    """Remove only revisions created by this migration and their pointers."""
    op.execute(
        sa.text(
            """
            UPDATE persons AS person
            SET published_revision_id = NULL,
                updated_at = now()
            WHERE person.published_revision_id IN (
                SELECT revision.id
                FROM publication_revisions AS revision
                WHERE revision.payload ->> '_backfilled_from_live' =
                    '0029_backfill_published_revision_pointer'
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM publication_revisions AS revision
            WHERE revision.payload ->> '_backfilled_from_live' =
                '0029_backfill_published_revision_pointer';
            """
        )
    )
