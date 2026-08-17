"""Seed countries and states of life required by the person editor.

Revision ID: 0002_seed_person_reference_data
Revises: 0001_initial_schema
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_seed_person_reference_data"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REFERENCE_NAMESPACE = uuid.UUID("7499d3a5-9a92-4da9-99c8-c7bba98ba77a")

COUNTRIES: list[tuple[str, str, str, str, str, str, str]] = [
    ("Albania", "Albania", "AL", "ALB", "Europa", "Tirana", "🇦🇱"),
    ("Argentyna", "Argentina", "AR", "ARG", "Ameryka Południowa", "Buenos Aires", "🇦🇷"),
    ("Australia", "Australia", "AU", "AUS", "Oceania", "Canberra", "🇦🇺"),
    ("Austria", "Austria", "AT", "AUT", "Europa", "Wiedeń", "🇦🇹"),
    ("Belgia", "Belgium", "BE", "BEL", "Europa", "Bruksela", "🇧🇪"),
    ("Boliwia", "Bolivia", "BO", "BOL", "Ameryka Południowa", "Sucre", "🇧🇴"),
    ("Bośnia i Hercegowina", "Bosnia and Herzegovina", "BA", "BIH", "Europa", "Sarajewo", "🇧🇦"),
    ("Brazylia", "Brazil", "BR", "BRA", "Ameryka Południowa", "Brasília", "🇧🇷"),
    ("Bułgaria", "Bulgaria", "BG", "BGR", "Europa", "Sofia", "🇧🇬"),
    ("Chile", "Chile", "CL", "CHL", "Ameryka Południowa", "Santiago", "🇨🇱"),
    ("Chiny", "China", "CN", "CHN", "Azja", "Pekin", "🇨🇳"),
    ("Chorwacja", "Croatia", "HR", "HRV", "Europa", "Zagrzeb", "🇭🇷"),
    ("Cypr", "Cyprus", "CY", "CYP", "Azja", "Nikozja", "🇨🇾"),
    ("Czechy", "Czechia", "CZ", "CZE", "Europa", "Praga", "🇨🇿"),
    ("Dania", "Denmark", "DK", "DNK", "Europa", "Kopenhaga", "🇩🇰"),
    ("Egipt", "Egypt", "EG", "EGY", "Afryka", "Kair", "🇪🇬"),
    ("Ekwador", "Ecuador", "EC", "ECU", "Ameryka Południowa", "Quito", "🇪🇨"),
    ("Etiopia", "Ethiopia", "ET", "ETH", "Afryka", "Addis Abeba", "🇪🇹"),
    ("Filipiny", "Philippines", "PH", "PHL", "Azja", "Manila", "🇵🇭"),
    ("Finlandia", "Finland", "FI", "FIN", "Europa", "Helsinki", "🇫🇮"),
    ("Francja", "France", "FR", "FRA", "Europa", "Paryż", "🇫🇷"),
    ("Grecja", "Greece", "GR", "GRC", "Europa", "Ateny", "🇬🇷"),
    ("Gruzja", "Georgia", "GE", "GEO", "Azja", "Tbilisi", "🇬🇪"),
    ("Hiszpania", "Spain", "ES", "ESP", "Europa", "Madryt", "🇪🇸"),
    ("Indie", "India", "IN", "IND", "Azja", "Nowe Delhi", "🇮🇳"),
    ("Irak", "Iraq", "IQ", "IRQ", "Azja", "Bagdad", "🇮🇶"),
    ("Irlandia", "Ireland", "IE", "IRL", "Europa", "Dublin", "🇮🇪"),
    ("Islandia", "Iceland", "IS", "ISL", "Europa", "Reykjavík", "🇮🇸"),
    ("Izrael", "Israel", "IL", "ISR", "Azja", "Jerozolima", "🇮🇱"),
    ("Japonia", "Japan", "JP", "JPN", "Azja", "Tokio", "🇯🇵"),
    ("Kanada", "Canada", "CA", "CAN", "Ameryka Północna", "Ottawa", "🇨🇦"),
    ("Kolumbia", "Colombia", "CO", "COL", "Ameryka Południowa", "Bogota", "🇨🇴"),
    ("Korea Południowa", "South Korea", "KR", "KOR", "Azja", "Seul", "🇰🇷"),
    ("Liban", "Lebanon", "LB", "LBN", "Azja", "Bejrut", "🇱🇧"),
    ("Litwa", "Lithuania", "LT", "LTU", "Europa", "Wilno", "🇱🇹"),
    ("Luksemburg", "Luxembourg", "LU", "LUX", "Europa", "Luksemburg", "🇱🇺"),
    ("Łotwa", "Latvia", "LV", "LVA", "Europa", "Ryga", "🇱🇻"),
    ("Malta", "Malta", "MT", "MLT", "Europa", "Valletta", "🇲🇹"),
    ("Meksyk", "Mexico", "MX", "MEX", "Ameryka Północna", "Meksyk", "🇲🇽"),
    ("Niderlandy", "Netherlands", "NL", "NLD", "Europa", "Amsterdam", "🇳🇱"),
    ("Niemcy", "Germany", "DE", "DEU", "Europa", "Berlin", "🇩🇪"),
    ("Norwegia", "Norway", "NO", "NOR", "Europa", "Oslo", "🇳🇴"),
    ("Nowa Zelandia", "New Zealand", "NZ", "NZL", "Oceania", "Wellington", "🇳🇿"),
    ("Palestyna", "Palestine", "PS", "PSE", "Azja", "Ramallah", "🇵🇸"),
    ("Peru", "Peru", "PE", "PER", "Ameryka Południowa", "Lima", "🇵🇪"),
    ("Polska", "Poland", "PL", "POL", "Europa", "Warszawa", "🇵🇱"),
    ("Portugalia", "Portugal", "PT", "PRT", "Europa", "Lizbona", "🇵🇹"),
    ("Rumunia", "Romania", "RO", "ROU", "Europa", "Bukareszt", "🇷🇴"),
    ("Serbia", "Serbia", "RS", "SRB", "Europa", "Belgrad", "🇷🇸"),
    ("Słowacja", "Slovakia", "SK", "SVK", "Europa", "Bratysława", "🇸🇰"),
    ("Słowenia", "Slovenia", "SI", "SVN", "Europa", "Lublana", "🇸🇮"),
    ("Stany Zjednoczone", "United States", "US", "USA", "Ameryka Północna", "Waszyngton", "🇺🇸"),
    ("Syria", "Syria", "SY", "SYR", "Azja", "Damaszek", "🇸🇾"),
    ("Szwajcaria", "Switzerland", "CH", "CHE", "Europa", "Berno", "🇨🇭"),
    ("Szwecja", "Sweden", "SE", "SWE", "Europa", "Sztokholm", "🇸🇪"),
    ("Turcja", "Türkiye", "TR", "TUR", "Azja", "Ankara", "🇹🇷"),
    ("Ukraina", "Ukraine", "UA", "UKR", "Europa", "Kijów", "🇺🇦"),
    ("Watykan", "Vatican City", "VA", "VAT", "Europa", "Watykan", "🇻🇦"),
    ("Węgry", "Hungary", "HU", "HUN", "Europa", "Budapeszt", "🇭🇺"),
    ("Wenezuela", "Venezuela", "VE", "VEN", "Ameryka Południowa", "Caracas", "🇻🇪"),
    ("Wielka Brytania", "United Kingdom", "GB", "GBR", "Europa", "Londyn", "🇬🇧"),
    ("Wietnam", "Vietnam", "VN", "VNM", "Azja", "Hanoi", "🇻🇳"),
    ("Włochy", "Italy", "IT", "ITA", "Europa", "Rzym", "🇮🇹"),
]

STATES_OF_LIFE: list[tuple[str, str, str]] = [
    ("Kapłan", "Priest", "Presbyter"),
    ("Biskup", "Bishop", "Episcopus"),
    ("Papież", "Pope", "Pontifex"),
    ("Diakon", "Deacon", "Diaconus"),
    ("Zakonnik / Mnich", "Religious (Male)", "Monachus"),
    ("Zakonnica", "Religious (Female)", "Monialis"),
    ("Osoba konsekrowana", "Consecrated Person", "Persona consecrata"),
    ("Świecki mężczyzna", "Lay Man", "Laicus"),
    ("Świecka kobieta", "Lay Woman", "Laica"),
    ("Pustelnik", "Hermit", "Eremita"),
    ("Dziewica konsekrowana", "Consecrated Virgin", "Virgo consecrata"),
    ("Wdowa / Wdowiec", "Widow / Widower", "Vidua"),
    ("Dziecko / Młodzieniec", "Child / Youth", "Puer / Iuvenis"),
    ("Nieznany", "Unknown", "Ignotus"),
]


def _reference_id(kind: str, key: str) -> str:
    return str(uuid.uuid5(REFERENCE_NAMESPACE, f"{kind}:{key}"))


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO countries (
                id, name_pl, name_en, iso_code_alpha2, iso_code_alpha3,
                continent, capital, flag_emoji, is_historical
            ) VALUES (
                CAST(:id AS uuid), :name_pl, :name_en, :iso2, :iso3,
                :continent, :capital, :flag, false
            )
            ON CONFLICT (iso_code_alpha2) DO NOTHING
            """
        ),
        [
            {
                "id": _reference_id("country", iso2),
                "name_pl": name_pl,
                "name_en": name_en,
                "iso2": iso2,
                "iso3": iso3,
                "continent": continent,
                "capital": capital,
                "flag": flag,
            }
            for name_pl, name_en, iso2, iso3, continent, capital, flag in COUNTRIES
        ],
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO states_of_life (id, name_pl, name_en, name_la)
            SELECT
                CAST(:id AS uuid),
                CAST(:name_pl AS varchar),
                CAST(:name_en AS varchar),
                CAST(:name_la AS varchar)
            WHERE NOT EXISTS (
                SELECT 1 FROM states_of_life
                WHERE lower(name_pl) = lower(CAST(:name_pl AS varchar))
            )
            """
        ),
        [
            {
                "id": _reference_id("state-of-life", name_en),
                "name_pl": name_pl,
                "name_en": name_en,
                "name_la": name_la,
            }
            for name_pl, name_en, name_la in STATES_OF_LIFE
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM states_of_life WHERE id = CAST(:id AS uuid)"),
        [{"id": _reference_id("state-of-life", name_en)} for _, name_en, _ in STATES_OF_LIFE],
    )
    bind.execute(
        sa.text("DELETE FROM countries WHERE id = CAST(:id AS uuid)"),
        [{"id": _reference_id("country", iso2)} for _, _, iso2, _, _, _, _ in COUNTRIES],
    )
