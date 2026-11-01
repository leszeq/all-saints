"""Add the Commemoration of All the Faithful Departed to Roman calendars."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_all_souls_observance"
down_revision: str | None = "0024_all_saints_observance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALL_SOULS_SLUG = "wszystkich-wiernych-zmarlych"


def upgrade() -> None:
    """Create the observance and its fixed-date calendar assignments."""
    op.execute(sa.text("""
            INSERT INTO liturgical_observances (
                slug,
                title_pl,
                title_en,
                latin_title,
                observance_type,
                summary_pl,
                description_pl,
                iconographic_attributes,
                is_featured,
                deleted_at,
                updated_at
            ) VALUES (
                :slug,
                'Wszystkich Wiernych Zmarłych',
                'All Souls',
                'Commemoratio Omnium Fidelium Defunctorum',
                'church',
                'Wspomnienie Wszystkich Wiernych Zmarłych przypada 2 listopada i jest dniem modlitwy za zmarłych.',
                'Kościół wspomina wszystkich wiernych zmarłych i modli się za tych, którzy oczekują pełni życia w Bogu.',
                'modlitwa za zmarłych; pamięć; nadzieja zmartwychwstania',
                true,
                NULL,
                now()
            )
            ON CONFLICT (slug) DO UPDATE SET
                title_pl = EXCLUDED.title_pl,
                title_en = EXCLUDED.title_en,
                latin_title = EXCLUDED.latin_title,
                observance_type = EXCLUDED.observance_type,
                summary_pl = EXCLUDED.summary_pl,
                description_pl = EXCLUDED.description_pl,
                iconographic_attributes = EXCLUDED.iconographic_attributes,
                is_featured = EXCLUDED.is_featured,
                deleted_at = NULL,
                updated_at = now()
            """).bindparams(slug=ALL_SOULS_SLUG))

    # The commemoration is the primary observance for this date in both calendars.
    op.execute(sa.text("""
            UPDATE feasts AS feast
            SET is_primary = false, updated_at = now()
            FROM liturgical_calendars AS calendar
            WHERE feast.calendar_id = calendar.id
              AND calendar.code IN ('roman_universal', 'roman_pl')
              AND feast.month = 11
              AND feast.day = 2
              AND feast.deleted_at IS NULL
            """))
    op.execute(sa.text("""
            UPDATE feasts AS feast
            SET
                month = 11,
                day = 2,
                day_of_year = 306,
                is_moveable = false,
                rank = 'memorial',
                liturgical_color = 'violet',
                is_primary = true,
                is_suppressed = false,
                source_title = 'Kalendarz liturgiczny Kościoła rzymskiego',
                notes = 'Wspomnienie Wszystkich Wiernych Zmarłych — 2 listopada.',
                updated_at = now()
            FROM liturgical_observances AS observance
            JOIN liturgical_calendars AS calendar
              ON calendar.code IN ('roman_universal', 'roman_pl')
            WHERE feast.observance_id = observance.id
              AND feast.calendar_id = calendar.id
              AND observance.slug = :slug
              AND feast.month = 11
              AND feast.day = 2
              AND feast.deleted_at IS NULL
            """).bindparams(slug=ALL_SOULS_SLUG))
    op.execute(sa.text("""
            INSERT INTO feasts (
                id,
                observance_id,
                calendar_id,
                month,
                day,
                day_of_year,
                is_moveable,
                rank,
                liturgical_color,
                is_primary,
                is_suppressed,
                source_title,
                notes
            )
            SELECT
                gen_random_uuid(),
                observance.id,
                calendar.id,
                11,
                2,
                306,
                false,
                'memorial',
                'violet',
                true,
                false,
                'Kalendarz liturgiczny Kościoła rzymskiego',
                'Wspomnienie Wszystkich Wiernych Zmarłych — 2 listopada.'
            FROM liturgical_observances AS observance
            CROSS JOIN liturgical_calendars AS calendar
            WHERE observance.slug = :slug
              AND calendar.code IN ('roman_universal', 'roman_pl')
              AND calendar.deleted_at IS NULL
              AND calendar.is_active = true
              AND NOT EXISTS (
                  SELECT 1
                  FROM feasts AS existing
                  WHERE existing.observance_id = observance.id
                    AND existing.calendar_id = calendar.id
                    AND existing.month = 11
                    AND existing.day = 2
                    AND existing.deleted_at IS NULL
              )
            """).bindparams(slug=ALL_SOULS_SLUG))


def downgrade() -> None:
    """Remove the migration-owned All Souls observance and assignments."""
    op.execute(sa.text("""
            DELETE FROM feasts
            WHERE observance_id IN (
                SELECT id FROM liturgical_observances WHERE slug = :slug
            )
            """).bindparams(slug=ALL_SOULS_SLUG))
    op.execute(
        sa.text("DELETE FROM liturgical_observances WHERE slug = :slug").bindparams(
            slug=ALL_SOULS_SLUG
        )
    )
