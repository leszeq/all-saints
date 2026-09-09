"""Unit tests for liturgical calendar ordering and import validation."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from src.application.services.calendar_query_service import CalendarQueryService
from src.application.services.calendar_service import CalendarService
from src.domain.hagiography.models import Person
from src.domain.liturgy.models import Feast, LiturgicalCalendar, LiturgicalObservance
from src.infrastructure.db.import_catalogue_persons import read_person_rows
from src.infrastructure.db.import_liturgical_calendar import read_rows
from src.infrastructure.db.import_liturgical_observances import read_observance_rows
from src.main import app
from src.presentation.api.v1.calendar.schemas import (
    FeastEntryCreateSchema,
    FeastEntryUpdateSchema,
)

DATA_DIRECTORY = Path(__file__).parents[2] / "data" / "liturgical-calendar"


def test_calendar_openapi_preserves_public_and_editorial_security_boundaries() -> None:
    paths = app.openapi()["paths"]

    public_operations = [
        paths["/api/v1/calendar/calendars"]["get"],
        paths["/api/v1/calendar/observances"]["get"],
        paths["/api/v1/calendar/observances/by-slug/{slug}"]["get"],
        paths["/api/v1/calendar/today"]["get"],
        paths["/api/v1/calendar/day/{value}"]["get"],
        paths["/api/v1/calendar/month/{year}/{month}"]["get"],
    ]
    editorial_operations = [
        paths["/api/v1/calendar/persons/{person_id}/entries"]["get"],
        paths["/api/v1/calendar/observances"]["post"],
        paths["/api/v1/calendar/observances/{observance_id}"]["patch"],
        paths["/api/v1/calendar/observances/{observance_id}"]["delete"],
        paths["/api/v1/calendar/entries"]["post"],
        paths["/api/v1/calendar/entries/{entry_id}"]["patch"],
        paths["/api/v1/calendar/entries/{entry_id}"]["delete"],
    ]

    assert all("security" not in operation for operation in public_operations)
    assert all(operation["security"] == [{"HTTPBearer": []}] for operation in editorial_operations)


@pytest.mark.asyncio
async def test_fixed_entry_query_executes_once() -> None:
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.unique.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    entries = await CalendarQueryService(db)._query_fixed_entries(
        calendar_codes=["roman_pl"],
        month=9,
        day=9,
    )

    assert entries == []
    db.execute.assert_awaited_once()


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


def _observance_feast(title: str, calendar: LiturgicalCalendar, *, primary: bool = False) -> Feast:
    observance = LiturgicalObservance(
        id=uuid.uuid4(),
        slug=title.lower().replace(" ", "-"),
        title_pl=title,
        observance_type="marian",
        is_featured=True,
    )
    feast = Feast(
        id=uuid.uuid4(),
        observance_id=observance.id,
        calendar_id=calendar.id,
        month=8,
        day=26,
        rank="solemnity",
        is_moveable=False,
        is_primary=primary,
        is_suppressed=False,
    )
    feast.observance = observance
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
    observance_payload = {
        "observance_id": uuid.uuid4(),
        "calendar_code": "roman_pl",
        "month": 2,
        "day": 29,
    }
    assert FeastEntryCreateSchema(**observance_payload).person_id is None

    with pytest.raises(ValidationError):
        FeastEntryCreateSchema(**{**payload, "day": 30})

    with pytest.raises(ValidationError):
        FeastEntryCreateSchema(**{**payload, "observance_id": uuid.uuid4()})

    with pytest.raises(ValidationError):
        FeastEntryCreateSchema(calendar_code="roman_pl", month=2, day=29)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FeastEntryCreateSchema(**payload, is_moveable=True)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FeastEntryUpdateSchema(date_note="Poniedziałek po Pięćdziesiątnicy")


def test_merge_supports_non_person_observance() -> None:
    polish = _calendar("roman_pl")
    mary = _observance_feast("Najświętsza Maryja Panna Częstochowska", polish, primary=True)

    entries = CalendarService._merge_and_sort([mary], "roman_pl")

    assert entries == [mary]
    assert entries[0].person is None
    assert entries[0].observance.title_pl == "Najświętsza Maryja Panna Częstochowska"


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


def test_august_24_dataset_contains_primary_feast_and_individual_blesseds() -> None:
    people = read_person_rows(DATA_DIRECTORY / "persons-08-24.csv")
    entries = [
        row
        for row in read_rows(DATA_DIRECTORY / "feasts.csv")
        if row["month"] == 8 and row["day"] == 24
    ]

    assert len(people) == 9
    assert len(entries) == 9
    primary = next(entry for entry in entries if entry["is_primary"])
    assert primary["person_slug"] == "sw-bartlomiej-apostol"
    assert primary["rank"] == "feast"
    assert primary["calendar_code"] == "roman_universal"
    assert all(
        entry["calendar_code"] == "roman_martyrology"
        for entry in entries
        if not entry["is_primary"]
    )
    assert {
        "bl-czeslaw-jozwiak",
        "bl-edward-kazmierski",
        "bl-edward-klinik",
        "bl-franciszek-kesy",
        "bl-jarogniew-wojciechowski",
    } <= {person["slug"] for person in people}
    emilia = next(person for person in people if person["slug"] == "sw-emilia-de-vialar")
    poznan_martyr = next(person for person in people if person["slug"] == "bl-czeslaw-jozwiak")
    assert emilia["canonization_date"] == "1951-06-24"
    assert emilia["beatification_year"] == "1939"
    assert poznan_martyr["beatification_date"] == "1999-06-13"


def test_august_25_dataset_contains_current_statuses_and_recognition_dates() -> None:
    people = read_person_rows(DATA_DIRECTORY / "persons-08-25.csv")
    entries = [
        row
        for row in read_rows(DATA_DIRECTORY / "feasts.csv")
        if row["month"] == 8 and row["day"] == 25
    ]

    assert len(people) == 5
    assert len(entries) == 5
    primary = next(entry for entry in entries if entry["is_primary"])
    assert primary["person_slug"] == "sw-ludwik-ix-krol-francji"
    assert primary["rank"] == "opt_memorial"
    assert {
        entry["person_slug"] for entry in entries if entry["calendar_code"] == "roman_universal"
    } == {"sw-ludwik-ix-krol-francji", "sw-jozef-kalasanty"}

    troncatti = next(person for person in people if person["slug"] == "sw-maria-troncatti")
    mariam = next(
        person
        for person in people
        if person["slug"] == "sw-maria-od-jezusa-ukrzyzowanego-mala-arabka"
    )
    assert troncatti["person_type"] == "saint"
    assert troncatti["canonization_date"] == "2025-10-19"
    assert troncatti["beatification_date"] == "2012-11-24"
    assert mariam["canonization_date"] == "2015-05-17"


def test_august_26_dataset_separates_polish_solemnity_from_martyrology() -> None:
    people = read_person_rows(DATA_DIRECTORY / "persons-08-26.csv")
    observances = read_observance_rows(DATA_DIRECTORY / "observances.csv")
    entries = [
        row
        for row in read_rows(DATA_DIRECTORY / "feasts.csv")
        if row["month"] == 8 and row["day"] == 26
    ]

    assert len(people) == 3
    assert len(entries) == 4
    primary = next(entry for entry in entries if entry["is_primary"])
    assert primary["person_slug"] is None
    assert primary["observance_slug"] == "najswietsza-maryja-panna-czestochowska"
    assert primary["calendar_code"] == "roman_pl"
    assert primary["rank"] == "solemnity"
    polish_observance = next(
        observance
        for observance in observances
        if observance["slug"] == "najswietsza-maryja-panna-czestochowska"
    )
    assert polish_observance["observance_type"] == "marian"
    assert all(
        entry["calendar_code"] == "roman_martyrology"
        for entry in entries
        if not entry["is_primary"]
    )

    teresa = next(
        person for person in people if person["slug"] == "sw-teresa-od-jezusa-jornet-e-ibars"
    )
    maria = next(
        person for person in people if person["slug"] == "bl-maria-od-aniolow-ginard-marti"
    )
    assert teresa["birth_year"] == "1843"
    assert teresa["beatification_date"] == "1958-04-27"
    assert teresa["canonization_date"] == "1974-01-27"
    assert maria["person_type"] == "blessed"
    assert maria["beatification_date"] == "2005-10-29"


def test_september_8_dataset_models_nativity_of_mary_as_observance() -> None:
    observances = read_observance_rows(DATA_DIRECTORY / "observances.csv")
    entries = [
        row
        for row in read_rows(DATA_DIRECTORY / "feasts.csv")
        if row["month"] == 9 and row["day"] == 8
    ]

    nativity = next(
        observance
        for observance in observances
        if observance["slug"] == "narodzenie-najswietszej-maryi-panny"
    )
    assert nativity["observance_type"] == "marian"
    assert nativity["title_pl"] == "Narodzenie Najświętszej Maryi Panny"
    assert "Protoewangelia Jakuba" in nativity["description_pl"]

    assert len(entries) == 1
    entry = entries[0]
    assert entry["person_slug"] is None
    assert entry["observance_slug"] == nativity["slug"]
    assert entry["calendar_code"] == "roman_universal"
    assert entry["rank"] == "feast"
    assert entry["liturgical_color"] == "white"
    assert entry["is_primary"] is True
