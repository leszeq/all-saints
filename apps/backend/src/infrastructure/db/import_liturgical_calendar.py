"""Idempotent CSV importer for fixed-date liturgical commemorations.

Run from ``apps/backend``::

    python -m src.infrastructure.db.import_liturgical_calendar \
        data/liturgical-calendar/feasts.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import text

from src.domain.hagiography.models import LiturgicalColor
from src.domain.liturgy.models import FeastRank
from src.infrastructure.db.import_catalogue_persons import (
    import_person_rows,
    read_person_rows,
)
from src.infrastructure.db.import_liturgical_observances import (
    import_observance_rows,
    read_observance_rows,
)
from src.infrastructure.db.session import get_engine


@dataclass(slots=True)
class ImportResult:
    """Counters returned by one import run."""

    created: int = 0
    updated: int = 0
    skipped: int = 0


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "tak"}


def read_rows(path: Path) -> list[dict[str, object]]:
    """Read and validate CSV rows before touching the database."""
    rows: list[dict[str, object]] = []
    valid_ranks = {rank.value for rank in FeastRank}
    valid_colors = {color.value for color in LiturgicalColor}

    with path.open(encoding="utf-8-sig", newline="") as source:
        for line_number, raw in enumerate(csv.DictReader(source), start=2):
            month = int(raw["month"])
            day = int(raw["day"])
            fixed_date = date(2000, month, day)
            rank = raw["rank"].strip()
            color = raw["liturgical_color"].strip()
            if rank not in valid_ranks:
                raise ValueError(f"Wiersz {line_number}: nieznana ranga {rank!r}")
            if color and color not in valid_colors:
                raise ValueError(f"Wiersz {line_number}: nieznany kolor {color!r}")
            person_slug = (raw.get("person_slug") or "").strip()
            observance_slug = (raw.get("observance_slug") or "").strip()
            if bool(person_slug) == bool(observance_slug):
                raise ValueError(
                    f"Wiersz {line_number}: podaj dokładnie person_slug albo observance_slug"
                )

            rows.append(
                {
                    "person_slug": person_slug or None,
                    "observance_slug": observance_slug or None,
                    "calendar_code": raw["calendar_code"].strip(),
                    "month": month,
                    "day": day,
                    "day_of_year": fixed_date.timetuple().tm_yday,
                    "rank": rank,
                    "liturgical_color": color or None,
                    "is_primary": _as_bool(raw["is_primary"]),
                    "source_title": raw["source_title"].strip() or None,
                    "source_url": raw["source_url"].strip() or None,
                    "notes": raw["notes"].strip() or None,
                }
            )
    return rows


async def import_rows(rows: list[dict[str, object]], *, dry_run: bool = False) -> ImportResult:
    """Upsert validated rows by person, calendar, and fixed date."""
    result = ImportResult()
    connection = await get_engine().connect()
    transaction = await connection.begin()
    try:
        for row in rows:
            calendar_id = (
                await connection.execute(
                    text(
                        """
                        SELECT c.id
                        FROM liturgical_calendars c
                        WHERE c.code = :calendar_code
                          AND c.deleted_at IS NULL
                          AND c.is_active = true
                        """
                    ),
                    row,
                )
            ).scalar_one_or_none()
            if calendar_id is None:
                result.skipped += 1
                continue

            person_id = None
            observance_id = None
            if row["person_slug"]:
                person_id = (
                    await connection.execute(
                        text(
                            """
                            SELECT id FROM persons
                            WHERE slug = :person_slug AND deleted_at IS NULL
                            """
                        ),
                        row,
                    )
                ).scalar_one_or_none()
            else:
                observance_id = (
                    await connection.execute(
                        text(
                            """
                            SELECT id FROM liturgical_observances
                            WHERE slug = :observance_slug AND deleted_at IS NULL
                            """
                        ),
                        row,
                    )
                ).scalar_one_or_none()
            if person_id is None and observance_id is None:
                result.skipped += 1
                continue

            values = {
                **row,
                "person_id": person_id,
                "observance_id": observance_id,
                "calendar_id": calendar_id,
            }
            if values["is_primary"]:
                await connection.execute(
                    text(
                        """
                        UPDATE feasts
                        SET is_primary = false, updated_at = now()
                        WHERE calendar_id = :calendar_id
                          AND month = :month
                          AND day = :day
                          AND deleted_at IS NULL
                          AND is_primary = true
                        """
                    ),
                    values,
                )

            existing_query = (
                text(
                    """
                    SELECT id FROM feasts
                    WHERE person_id = :target_id
                      AND calendar_id = :calendar_id
                      AND month = :month AND day = :day AND deleted_at IS NULL
                    """
                )
                if person_id is not None
                else text(
                    """
                    SELECT id FROM feasts
                    WHERE observance_id = :target_id
                      AND calendar_id = :calendar_id
                      AND month = :month AND day = :day AND deleted_at IS NULL
                    """
                )
            )
            existing_id = (
                await connection.execute(
                    existing_query,
                    {
                        **values,
                        "target_id": person_id if person_id is not None else observance_id,
                    },
                )
            ).scalar_one_or_none()

            if existing_id is None:
                await connection.execute(
                    text(
                        """
                        INSERT INTO feasts (
                            id, person_id, observance_id, calendar_id, month, day, day_of_year,
                            is_moveable, rank, liturgical_color, is_primary,
                            is_suppressed, source_title, source_url, notes
                        ) VALUES (
                            :id, :person_id, :observance_id, :calendar_id, :month, :day, :day_of_year,
                            false, :rank, :liturgical_color, :is_primary,
                            false, :source_title, :source_url, :notes
                        )
                        """
                    ),
                    {**values, "id": uuid.uuid4()},
                )
                result.created += 1
            else:
                await connection.execute(
                    text(
                        """
                        UPDATE feasts
                        SET day_of_year = :day_of_year,
                            rank = :rank,
                            liturgical_color = :liturgical_color,
                            is_primary = :is_primary,
                            source_title = :source_title,
                            source_url = :source_url,
                            notes = :notes,
                            updated_at = now()
                        WHERE id = :id
                        """
                    ),
                    {**values, "id": existing_id},
                )
                result.updated += 1

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
    parser = argparse.ArgumentParser(description="Import liturgical feast assignments from CSV")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--persons",
        type=Path,
        action="append",
        default=[],
        help="Repeatable catalogue-person CSV imported before calendar assignments",
    )
    parser.add_argument(
        "--observances",
        type=Path,
        action="append",
        default=[],
        help="Repeatable non-person observance CSV imported before calendar assignments",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    person_results = [
        await import_person_rows(
            read_person_rows(person_path),
            source_label=str(person_path),
            dry_run=args.dry_run,
        )
        for person_path in args.persons
    ]
    observance_results = [
        await import_observance_rows(
            read_observance_rows(observance_path),
            dry_run=args.dry_run,
        )
        for observance_path in args.observances
    ]
    rows = read_rows(args.path)
    result = await import_rows(rows, dry_run=args.dry_run)
    mode = "DRY RUN" if args.dry_run else "IMPORTED"
    person_summary = (
        f"persons_created={sum(item.created for item in person_results)}, "
        f"persons_existing={sum(item.existing for item in person_results)}, "
        if person_results
        else ""
    )
    observance_summary = (
        f"observances_created={sum(item.created for item in observance_results)}, "
        f"observances_updated={sum(item.updated for item in observance_results)}, "
        if observance_results
        else ""
    )
    print(
        f"{mode}: {person_summary}{observance_summary}created={result.created}, "
        f"updated={result.updated}, "
        f"skipped_missing_relations={result.skipped}"
    )


if __name__ == "__main__":
    asyncio.run(_main())
