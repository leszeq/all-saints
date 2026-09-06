"""Idempotent CSV importer for non-person liturgical observances."""

from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from src.domain.liturgy.models import ObservanceType
from src.infrastructure.db.session import get_engine


@dataclass(slots=True)
class ObservanceImportResult:
    """Counters returned by an observance import run."""

    created: int = 0
    updated: int = 0


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "tak"}


def read_observance_rows(path: Path) -> list[dict[str, object]]:
    """Read and validate non-person observances from a UTF-8 CSV file."""
    rows: list[dict[str, object]] = []
    valid_types = {item.value for item in ObservanceType}
    with path.open(encoding="utf-8-sig", newline="") as source:
        for line_number, raw in enumerate(csv.DictReader(source), start=2):
            observance_type = raw["observance_type"].strip()
            if observance_type not in valid_types:
                raise ValueError(f"Wiersz {line_number}: nieznany typ obchodu {observance_type!r}")
            slug = raw["slug"].strip()
            title_pl = raw["title_pl"].strip()
            if not slug or not title_pl:
                raise ValueError(f"Wiersz {line_number}: slug i title_pl są wymagane")
            rows.append(
                {
                    "slug": slug,
                    "title_pl": title_pl,
                    "title_en": raw["title_en"].strip() or None,
                    "latin_title": raw["latin_title"].strip() or None,
                    "observance_type": observance_type,
                    "summary_pl": raw["summary_pl"].strip() or None,
                    "description_pl": raw["description_pl"].strip() or None,
                    "iconographic_attributes": raw["iconographic_attributes"].strip() or None,
                    "is_featured": _as_bool(raw["is_featured"]),
                }
            )
    return rows


async def import_observance_rows(
    rows: list[dict[str, object]], *, dry_run: bool = False
) -> ObservanceImportResult:
    """Upsert observances by their stable slug."""
    result = ObservanceImportResult()
    connection = await get_engine().connect()
    transaction = await connection.begin()
    try:
        for row in rows:
            existing_id = (
                await connection.execute(
                    text("SELECT id FROM liturgical_observances WHERE slug = :slug"),
                    row,
                )
            ).scalar_one_or_none()
            if existing_id is None:
                await connection.execute(
                    text("""
                        INSERT INTO liturgical_observances (
                            id, slug, title_pl, title_en, latin_title, observance_type,
                            summary_pl, description_pl, iconographic_attributes, is_featured
                        ) VALUES (
                            :id, :slug, :title_pl, :title_en, :latin_title, :observance_type,
                            :summary_pl, :description_pl, :iconographic_attributes, :is_featured
                        )
                        """),
                    {**row, "id": uuid.uuid4()},
                )
                result.created += 1
            else:
                await connection.execute(
                    text("""
                        UPDATE liturgical_observances
                        SET title_pl = :title_pl,
                            title_en = :title_en,
                            latin_title = :latin_title,
                            observance_type = :observance_type,
                            summary_pl = :summary_pl,
                            description_pl = :description_pl,
                            iconographic_attributes = :iconographic_attributes,
                            is_featured = :is_featured,
                            deleted_at = NULL,
                            updated_at = now()
                        WHERE id = :id
                        """),
                    {**row, "id": existing_id},
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
    parser = argparse.ArgumentParser(description="Import non-person liturgical observances")
    parser.add_argument("path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = await import_observance_rows(
        read_observance_rows(args.path),
        dry_run=args.dry_run,
    )
    mode = "DRY RUN" if args.dry_run else "IMPORTED"
    print(f"{mode}: created={result.created}, updated={result.updated}")


if __name__ == "__main__":
    asyncio.run(_main())
