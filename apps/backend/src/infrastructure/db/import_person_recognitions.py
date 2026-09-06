"""Idempotent importer for documented beatification and canonization dates."""

from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import text

from src.infrastructure.db.session import get_engine


@dataclass(slots=True)
class RecognitionImportResult:
    """Counters reported after importing recognition facts."""

    imported: int = 0
    skipped_missing_person: int = 0


def _as_int(value: str) -> int | None:
    return int(value) if value else None


def _validate_date(value: str, *, field: str, line_number: int) -> None:
    if not value:
        return
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Wiersz {line_number}: {field} musi mieć format RRRR-MM-DD") from exc


def read_recognition_rows(path: Path) -> list[dict[str, str]]:
    """Read and validate recognition rows before touching the database."""
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as source:
        for line_number, raw in enumerate(csv.DictReader(source), start=2):
            row = {key: (value or "").strip() for key, value in raw.items()}
            if not row["person_slug"]:
                raise ValueError(f"Wiersz {line_number}: brak person_slug")
            _validate_date(
                row["beatification_date"],
                field="beatification_date",
                line_number=line_number,
            )
            _validate_date(
                row["canonization_date"],
                field="canonization_date",
                line_number=line_number,
            )
            if not any(
                row[field]
                for field in (
                    "beatification_date",
                    "beatification_year",
                    "canonization_date",
                    "canonization_year",
                )
            ):
                raise ValueError(f"Wiersz {line_number}: brak daty lub roku procesu")
            rows.append(row)
    return rows


async def import_recognition_rows(
    rows: list[dict[str, str]],
    *,
    dry_run: bool = False,
) -> RecognitionImportResult:
    """Upsert recognition records for people already present in the catalogue."""
    result = RecognitionImportResult()
    connection = await get_engine().connect()
    transaction = await connection.begin()
    try:
        for row in rows:
            person_id = (
                await connection.execute(
                    text("""
                        SELECT id FROM persons
                        WHERE slug = :person_slug AND deleted_at IS NULL
                        """),
                    row,
                )
            ).scalar_one_or_none()
            if person_id is None:
                result.skipped_missing_person += 1
                continue

            notes = f"{row['source_title']}: {row['source_url']}"
            beatification_year = _as_int(row["beatification_year"])
            if row["beatification_date"] or beatification_year:
                await connection.execute(
                    text("""
                        INSERT INTO beatifications (
                            id, person_id, beatification_date, beatification_year, notes
                        ) VALUES (
                            :id, :person_id, :recognition_date, :recognition_year, :notes
                        )
                        ON CONFLICT (person_id) DO UPDATE SET
                            beatification_date = EXCLUDED.beatification_date,
                            beatification_year = EXCLUDED.beatification_year,
                            notes = EXCLUDED.notes,
                            updated_at = now()
                        """),
                    {
                        "id": uuid.uuid4(),
                        "person_id": person_id,
                        "recognition_date": row["beatification_date"] or None,
                        "recognition_year": beatification_year,
                        "notes": notes,
                    },
                )

            canonization_year = _as_int(row["canonization_year"])
            if row["canonization_date"] or canonization_year:
                await connection.execute(
                    text("""
                        INSERT INTO canonizations (
                            id, person_id, canonization_date, canonization_year, notes
                        ) VALUES (
                            :id, :person_id, :recognition_date, :recognition_year, :notes
                        )
                        ON CONFLICT (person_id) DO UPDATE SET
                            canonization_date = EXCLUDED.canonization_date,
                            canonization_year = EXCLUDED.canonization_year,
                            notes = EXCLUDED.notes,
                            updated_at = now()
                        """),
                    {
                        "id": uuid.uuid4(),
                        "person_id": person_id,
                        "recognition_date": row["canonization_date"] or None,
                        "recognition_year": canonization_year,
                        "notes": notes,
                    },
                )
            result.imported += 1

        if dry_run:
            await transaction.rollback()
        else:
            await transaction.commit()
        return result
    except Exception:
        await transaction.rollback()
        raise
    finally:
        await connection.close()


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Import documented beatification and canonization dates"
    )
    parser.add_argument("path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = await import_recognition_rows(
        read_recognition_rows(args.path),
        dry_run=args.dry_run,
    )
    mode = "DRY RUN" if args.dry_run else "IMPORTED"
    print(
        f"{mode}: imported={result.imported}, "
        f"skipped_missing_person={result.skipped_missing_person}"
    )


if __name__ == "__main__":
    asyncio.run(_main())
