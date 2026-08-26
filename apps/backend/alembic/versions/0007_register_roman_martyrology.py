"""Register the Roman Martyrology as a separate catalogue layer.

Revision ID: 0007_register_roman_martyrology
Revises: 0006_expand_religious_orders
"""

from __future__ import annotations

from alembic import op

revision: str = "0007_register_roman_martyrology"
down_revision: str | None = "0006_expand_religious_orders"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Add a separately labelled source for non-liturgical daily commemorations."""
    op.execute(
        """
        INSERT INTO liturgical_calendars (
            id, code, name, rite, scope, description, is_active
        ) VALUES (
            gen_random_uuid(),
            'roman_martyrology',
            'Martyrologium Rzymskie',
            'roman',
            'universal',
            'Katalog świętych i błogosławionych według daty, odrębny od Ogólnego Kalendarza Rzymskiego.',
            true
        )
        ON CONFLICT (code) DO UPDATE SET
            name = EXCLUDED.name,
            rite = EXCLUDED.rite,
            scope = EXCLUDED.scope,
            description = EXCLUDED.description,
            is_active = true,
            deleted_at = NULL
        """
    )


def downgrade() -> None:
    """Remove the separately registered Martyrology calendar."""
    op.execute("DELETE FROM liturgical_calendars WHERE code = 'roman_martyrology'")
