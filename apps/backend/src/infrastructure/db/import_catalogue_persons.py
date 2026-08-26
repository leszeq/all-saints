"""Reusable importer for versioned hagiographic person records."""

from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from src.domain.hagiography.models import Era, Gender, PersonType, PublicationStatus
from src.infrastructure.db.session import get_engine


@dataclass(slots=True)
class PersonImportResult:
    """Counters returned after importing catalogue people."""

    created: int = 0
    existing: int = 0


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "tak"}


def _as_int(value: str) -> int | None:
    return int(value) if value else None


async def _upsert_recognition_records(
    connection: AsyncConnection,
    person_id: uuid.UUID,
    row: dict[str, str],
) -> None:
    """Persist optional beatification and canonization facts from a person row."""
    beatification_date = row.get("beatification_date", "")
    beatification_year = _as_int(row.get("beatification_year", ""))
    if beatification_date or beatification_year:
        await connection.execute(
            text(
                """
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
                """
            ),
            {
                "id": uuid.uuid4(),
                "person_id": person_id,
                "recognition_date": beatification_date or None,
                "recognition_year": beatification_year,
                "notes": f"Źródło danych: {row['source_url']}",
            },
        )

    canonization_date = row.get("canonization_date", "")
    canonization_year = _as_int(row.get("canonization_year", ""))
    if canonization_date or canonization_year:
        await connection.execute(
            text(
                """
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
                """
            ),
            {
                "id": uuid.uuid4(),
                "person_id": person_id,
                "recognition_date": canonization_date or None,
                "recognition_year": canonization_year,
                "notes": f"Źródło danych: {row['source_url']}",
            },
        )


def read_person_rows(path: Path) -> list[dict[str, str]]:
    """Read and validate a catalogue-person CSV file."""
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(source)
        ]

    person_types = {item.value for item in PersonType}
    statuses = {item.value for item in PublicationStatus}
    genders = {item.value for item in Gender}
    eras = {item.value for item in Era}
    for row in rows:
        if row["person_type"] not in person_types:
            raise ValueError(f"Nieznany typ osoby: {row['person_type']}")
        if row["status"] not in statuses:
            raise ValueError(f"Nieznany status osoby: {row['status']}")
        if row["gender"] not in genders:
            raise ValueError(f"Nieznana płeć: {row['gender']}")
        if row["era"] and row["era"] not in eras:
            raise ValueError(f"Nieznana epoka: {row['era']}")
    return rows


async def import_person_rows_on_connection(
    connection: AsyncConnection,
    rows: list[dict[str, str]],
    *,
    source_label: str,
) -> PersonImportResult:
    """Insert missing people using an existing transaction."""
    result = PersonImportResult()
    for row in rows:
        existing_id = (
            await connection.execute(
                text("SELECT id FROM persons WHERE slug = :slug AND deleted_at IS NULL"),
                row,
            )
        ).scalar_one_or_none()
        if existing_id is not None:
            result.existing += 1
            person_id = existing_id
        else:
            state_of_life_id = (
                await connection.execute(
                    text(
                        """
                        SELECT id FROM states_of_life
                        WHERE name_pl = :state_of_life_name AND deleted_at IS NULL
                        """
                    ),
                    row,
                )
            ).scalar_one_or_none()
            person_id = uuid.uuid4()
            values = {
                **row,
                "id": person_id,
                "century": _as_int(row["century"]),
                "birth_year": _as_int(row["birth_year"]),
                "death_year": _as_int(row["death_year"]),
                "state_of_life_id": state_of_life_id,
                "is_featured": _as_bool(row["is_featured"]),
                "external_ids": json.dumps(
                    {"editorial_source_url": row["source_url"]}, ensure_ascii=False
                ),
            }
            await connection.execute(
                text(
                    """
                    INSERT INTO persons (
                        id, slug, canonical_name, canonical_name_en, latin_name,
                        person_type, status, gender, era, century, birth_year,
                        death_year, state_of_life_id, summary_pl, biography_pl,
                        iconographic_attributes, is_featured, external_ids, version
                    ) VALUES (
                        :id, :slug, :canonical_name, :canonical_name_en, :latin_name,
                        :person_type, :status, :gender, :era, :century, :birth_year,
                        :death_year, :state_of_life_id, :summary_pl, :biography_pl,
                        :iconographic_attributes, :is_featured,
                        CAST(:external_ids AS jsonb), 1
                    )
                    """
                ),
                values,
            )
            snapshot = {
                "id": str(person_id),
                "slug": row["slug"],
                "canonical_name": row["canonical_name"],
                "person_type": row["person_type"],
                "status": row["status"],
                "source": source_label,
            }
            await connection.execute(
                text(
                    """
                    INSERT INTO person_versions (
                        id, person_id, version_number, snapshot, changed_at, change_summary
                    ) VALUES (
                        :id, :person_id, 1, CAST(:snapshot AS jsonb),
                        :changed_at, :change_summary
                    )
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "person_id": person_id,
                    "snapshot": json.dumps(snapshot, ensure_ascii=False),
                    "changed_at": datetime.now(UTC).isoformat(),
                    "change_summary": "Import danych kalendarza świętych",
                },
            )
            result.created += 1

        await _upsert_recognition_records(connection, person_id, row)
    return result


async def import_person_rows(
    rows: list[dict[str, str]],
    *,
    source_label: str,
    dry_run: bool = False,
) -> PersonImportResult:
    """Import person rows in their own transaction."""
    connection = await get_engine().connect()
    transaction = await connection.begin()
    try:
        result = await import_person_rows_on_connection(
            connection,
            rows,
            source_label=source_label,
        )
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
