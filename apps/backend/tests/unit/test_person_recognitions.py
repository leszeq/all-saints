"""Tests for versioned beatification and canonization data."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.db.import_person_recognitions import read_recognition_rows

DATA_FILE = Path(__file__).parents[2] / "data" / "hagiography" / "recognitions.csv"


def test_recognition_dataset_contains_documented_modern_saints() -> None:
    rows = read_recognition_rows(DATA_FILE)

    john_paul = next(row for row in rows if row["person_slug"] == "sw-jan-pawel-ii")
    faustina = next(row for row in rows if row["person_slug"] == "sw-faustyna-kowalska")
    assert john_paul["beatification_date"] == "2011-05-01"
    assert john_paul["canonization_date"] == "2014-04-27"
    assert faustina["beatification_date"] == "1993-04-18"
    assert faustina["canonization_date"] == "2000-04-30"


def test_recognition_reader_rejects_invalid_exact_date(tmp_path: Path) -> None:
    path = tmp_path / "recognitions.csv"
    path.write_text(
        "person_slug,beatification_date,beatification_year,canonization_date,"
        "canonization_year,source_title,source_url\n"
        "sw-przyklad,2026-02-30,2026,,,Źródło,https://example.com\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="RRRR-MM-DD"):
        read_recognition_rows(path)
