"""Unit tests for liturgical calendar ordering and import validation."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.application.services.calendar_service import CalendarService
from src.domain.hagiography.models import Person
from src.domain.liturgy.models import Feast, LiturgicalCalendar
from src.infrastructure.db.import_liturgical_calendar import read_rows
from src.presentation.api.v1.calendar.schemas import FeastEntryCreateSchema


def _person(name: str, *, featured: bool = False) -> Person:
    return Person(
        id=uuid.uuid4(),
        slug=name.lower().replace(" ", "-"),
        canonical_name=name,
        person_type="saint",
        status="published",
        gender="unknown",
        is_featured=featured,
    )


def _calendar(code: str) -> LiturgicalCalendar:
    return LiturgicalCalendar(
        id=uuid.uuid4(),
        code=code,
        name=code,
        rite="roman",
        scope="national" if code == "roman_pl" else "universal",
        is_active=True,
    )


def _feast(person: Person, calendar: LiturgicalCalendar, *, primary: bool = False) -> Feast:
    feast = Feast(
        id=uuid.uuid4(),
        person_id=person.id,
        calendar_id=calendar.id,
        month=8,
        day=23,
        rank="opt_memorial",
        is_moveable=False,
        is_primary=primary,
        is_suppressed=False,
    )
    feast.person = person
    feast.calendar = calendar
    return feast


def test_merge_prefers_explicit_primary_and_deduplicates_local_assignment() -> None:
    universal = _calendar("roman_universal")
    polish = _calendar("roman_pl")
    rose = _person("Św. Róża z Limy")
    repeated = _person("Św. Przykład", featured=True)

    entries = CalendarService._merge_and_sort(
        [
            _feast(repeated, universal),
            _feast(repeated, polish),
            _feast(rose, universal, primary=True),
        ],
        "roman_pl",
    )

    assert [entry.person.canonical_name for entry in entries] == [
        "Św. Róża z Limy",
        "Św. Przykład",
    ]
    assert entries[1].calendar.code == "roman_pl"


def test_create_schema_accepts_leap_day_and_rejects_impossible_date() -> None:
    payload = {
        "person_id": uuid.uuid4(),
        "calendar_code": "roman_pl",
        "month": 2,
        "day": 29,
    }
    assert FeastEntryCreateSchema(**payload).day == 29

    with pytest.raises(ValidationError):
        FeastEntryCreateSchema(**{**payload, "day": 30})


def test_csv_reader_normalizes_import_fields(tmp_path: Path) -> None:
    path = tmp_path / "feasts.csv"
    path.write_text(
        "calendar_code,person_slug,month,day,rank,liturgical_color,is_primary,"
        "source_title,source_url,notes\n"
        "roman_pl,sw-przyklad,2,29,memorial,white,tak,Dokument,https://example.com,Notatka\n",
        encoding="utf-8",
    )

    rows = read_rows(path)

    assert rows[0]["day_of_year"] == 60
    assert rows[0]["is_primary"] is True
    assert rows[0]["liturgical_color"] == "white"
