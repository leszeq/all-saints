"""Expand the country dictionary to the complete ISO 3166-1 catalogue.

Revision ID: 0009_expand_countries
Revises: 0008_add_liturgical_observances
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from babel import Locale


revision: str = "0009_expand_countries"
down_revision: str | None = "0008_add_liturgical_observances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REFERENCE_NAMESPACE = uuid.UUID("7499d3a5-9a92-4da9-99c8-c7bba98ba77a")

# CLDR also exposes a few grouping, testing and user-assigned codes. Removing
# these entries leaves the 249 current ISO 3166-1 countries and territories.
NON_ISO_CLDR_CODES = {
    "AC",
    "CP",
    "DG",
    "EA",
    "EU",
    "EZ",
    "IC",
    "QO",
    "TA",
    "UN",
    "XA",
    "XB",
    "XK",
    "ZZ",
}

# These entries were introduced by 0002 and must remain owned by that migration
# when this revision is downgraded.
INITIAL_COUNTRY_CODES = {
    "AL", "AR", "AU", "AT", "BE", "BO", "BA", "BR", "BG", "CL", "CN",
    "HR", "CY", "CZ", "DK", "EG", "EC", "ET", "PH", "FI", "FR", "GR",
    "GE", "ES", "IN", "IQ", "IE", "IS", "IL", "JP", "CA", "CO", "KR",
    "LB", "LT", "LU", "LV", "MT", "MX", "NL", "DE", "NO", "NZ", "PS",
    "PE", "PL", "PT", "RO", "RS", "SK", "SI", "US", "SY", "CH", "SE",
    "TR", "UA", "VA", "HU", "VE", "GB", "VN", "IT",
}


def _reference_id(iso2: str) -> str:
    return str(uuid.uuid5(REFERENCE_NAMESPACE, f"country:{iso2}"))


def _flag_emoji(iso2: str) -> str:
    return "".join(chr(127397 + ord(character)) for character in iso2)


def _iso_country_codes(locale: Locale) -> list[str]:
    return sorted(
        code
        for code in locale.territories
        if len(code) == 2
        and code.isalpha()
        and code not in NON_ISO_CLDR_CODES
    )


def upgrade() -> None:
    """Insert missing countries and territories with localized CLDR names."""
    polish = Locale("pl")
    english = Locale("en")
    codes = _iso_country_codes(polish)
    if len(codes) != 249:
        raise RuntimeError(f"Expected 249 ISO 3166-1 entries, received {len(codes)}")

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO countries (
                id, name_pl, name_en, iso_code_alpha2, flag_emoji, is_historical
            ) VALUES (
                CAST(:id AS uuid), :name_pl, :name_en, :iso2, :flag, false
            )
            ON CONFLICT (iso_code_alpha2) DO NOTHING
            """
        ),
        [
            {
                "id": _reference_id(code),
                "name_pl": str(polish.territories[code]),
                "name_en": str(english.territories[code]),
                "iso2": code,
                "flag": _flag_emoji(code),
            }
            for code in codes
        ],
    )


def downgrade() -> None:
    """Remove only entries introduced by this migration."""
    polish = Locale("pl")
    inserted_codes = [
        code
        for code in _iso_country_codes(polish)
        if code not in INITIAL_COUNTRY_CODES
    ]
    op.get_bind().execute(
        sa.text("DELETE FROM countries WHERE id = CAST(:id AS uuid)"),
        [{"id": _reference_id(code)} for code in inserted_codes],
    )
