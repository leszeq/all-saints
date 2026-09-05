"""Idempotent importer for religious communities and person memberships."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from src.domain.geography.models import (
    OrderCharism,
    OrderMembershipType,
    ReligiousCommunityType,
)
from src.domain.hagiography.models import Era, Gender, PersonType, PublicationStatus
from src.infrastructure.db.session import get_engine


@dataclass(slots=True)
class ImportResult:
    """Counters reported after a community data import."""

    persons_created: int = 0
    persons_existing: int = 0
    orders_created: int = 0
    orders_updated: int = 0
    memberships_created: int = 0
    memberships_updated: int = 0
    memberships_skipped: int = 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(source)
        ]


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "tak"}


def _as_int(value: str) -> int | None:
    return int(value) if value else None


def read_dataset(directory: Path) -> tuple[list[dict[str, str]], ...]:
    """Read and validate all three versioned CSV files."""
    people = _read_csv(directory / "persons.csv")
    orders = _read_csv(directory / "orders.csv")
    memberships = _read_csv(directory / "memberships.csv")

    person_types = {item.value for item in PersonType}
    statuses = {item.value for item in PublicationStatus}
    genders = {item.value for item in Gender}
    eras = {item.value for item in Era}
    community_types = {item.value for item in ReligiousCommunityType}
    charisms = {item.value for item in OrderCharism}
    membership_types = {item.value for item in OrderMembershipType}

    for row in people:
        if row["person_type"] not in person_types:
            raise ValueError(f"Nieznany typ osoby: {row['person_type']}")
        if row["status"] not in statuses:
            raise ValueError(f"Nieznany status osoby: {row['status']}")
        if row["gender"] not in genders:
            raise ValueError(f"Nieznana płeć: {row['gender']}")
        if row["era"] and row["era"] not in eras:
            raise ValueError(f"Nieznana epoka: {row['era']}")
    for row in orders:
        if row["community_type"] not in community_types:
            raise ValueError(f"Nieznany typ wspólnoty: {row['community_type']}")
        if row["charism"] and row["charism"] not in charisms:
            raise ValueError(f"Nieznany charyzmat: {row['charism']}")
    for row in memberships:
        if row["membership_type"] not in membership_types:
            raise ValueError(f"Nieznany typ członkostwa: {row['membership_type']}")
    return people, orders, memberships


async def import_dataset(directory: Path, *, dry_run: bool = False) -> ImportResult:
    """Import people, communities, and their relations in one transaction."""
    people, orders, memberships = read_dataset(directory)
    result = ImportResult()
    connection = await get_engine().connect()
    transaction = await connection.begin()
    try:
        for row in people:
            existing_id = (
                await connection.execute(
                    text("SELECT id FROM persons WHERE slug = :slug AND deleted_at IS NULL"),
                    row,
                )
            ).scalar_one_or_none()
            if existing_id is not None:
                result.persons_existing += 1
                continue

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
                "source": "religious-orders/persons.csv",
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
                    "change_summary": "Import danych wspólnot zakonnych",
                },
            )
            result.persons_created += 1

        for row in orders:
            founder_id = None
            if row["founder_slug"]:
                founder_id = (
                    await connection.execute(
                        text("SELECT id FROM persons WHERE slug = :founder_slug"), row
                    )
                ).scalar_one_or_none()
            values = {
                **row,
                "founded_year": _as_int(row["founded_year"]),
                "founder_id": founder_id,
                "papal_approval_year": _as_int(row["papal_approval_year"]),
                "is_featured": _as_bool(row["is_featured"]),
                "sort_order": int(row["sort_order"] or 0),
            }
            existing_id = (
                await connection.execute(
                    text("SELECT id FROM religious_orders WHERE slug = :slug"), values
                )
            ).scalar_one_or_none()
            if existing_id is None:
                await connection.execute(
                    text(
                        """
                        INSERT INTO religious_orders (
                            id, slug, name, name_la, name_local, abbreviation,
                            community_type, spiritual_family, founded_year, founder_id,
                            founder_name, papal_approval_year, charism, description,
                            history, mission, motto, website_url, source_title,
                            source_url, is_featured, sort_order, is_suppressed
                        ) VALUES (
                            :id, :slug, :name, :name_la, :name_local, :abbreviation,
                            :community_type, :spiritual_family, :founded_year, :founder_id,
                            :founder_name, :papal_approval_year, :charism, :description,
                            :history, :mission, :motto, :website_url, :source_title,
                            :source_url, :is_featured, :sort_order, false
                        )
                        """
                    ),
                    {**values, "id": uuid.uuid4()},
                )
                result.orders_created += 1
            else:
                await connection.execute(
                    text(
                        """
                        UPDATE religious_orders SET
                            name = :name, name_la = :name_la, name_local = :name_local,
                            abbreviation = :abbreviation, community_type = :community_type,
                            spiritual_family = :spiritual_family, founded_year = :founded_year,
                            founder_id = :founder_id, founder_name = :founder_name,
                            papal_approval_year = :papal_approval_year, charism = :charism,
                            description = :description, history = :history, mission = :mission,
                            motto = :motto, website_url = :website_url,
                            source_title = :source_title, source_url = :source_url,
                            is_featured = :is_featured, sort_order = :sort_order,
                            is_suppressed = false, deleted_at = NULL, updated_at = now()
                        WHERE id = :id
                        """
                    ),
                    {**values, "id": existing_id},
                )
                result.orders_updated += 1

        for row in memberships:
            resolved = (
                await connection.execute(
                    text(
                        """
                        SELECT p.id AS person_id, r.id AS order_id
                        FROM persons p
                        CROSS JOIN religious_orders r
                        WHERE p.slug = :person_slug AND p.deleted_at IS NULL
                          AND r.slug = :order_slug AND r.deleted_at IS NULL
                        """
                    ),
                    row,
                )
            ).mappings().one_or_none()
            if resolved is None:
                result.memberships_skipped += 1
                continue
            values = {
                **row,
                "person_id": resolved["person_id"],
                "order_id": resolved["order_id"],
                "is_founder": _as_bool(row["is_founder"]),
                "entry_date": row["entry_date"] or None,
                "exit_date": row["exit_date"] or None,
                "notes": row["notes"] or None,
            }
            existing = (
                await connection.execute(
                    text(
                        """
                        SELECT 1 FROM person_orders
                        WHERE person_id = :person_id AND order_id = :order_id
                        """
                    ),
                    values,
                )
            ).scalar_one_or_none()
            if existing is None:
                await connection.execute(
                    text(
                        """
                        INSERT INTO person_orders (
                            person_id, order_id, entry_date, exit_date, is_founder,
                            membership_type, notes
                        ) VALUES (
                            :person_id, :order_id, :entry_date, :exit_date, :is_founder,
                            :membership_type, :notes
                        )
                        """
                    ),
                    values,
                )
                result.memberships_created += 1
            else:
                await connection.execute(
                    text(
                        """
                        UPDATE person_orders SET
                            entry_date = :entry_date, exit_date = :exit_date,
                            is_founder = :is_founder, membership_type = :membership_type,
                            notes = :notes
                        WHERE person_id = :person_id AND order_id = :order_id
                        """
                    ),
                    values,
                )
                result.memberships_updated += 1

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
    parser = argparse.ArgumentParser(description="Import religious orders and memberships")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = await import_dataset(args.directory, dry_run=args.dry_run)
    mode = "DRY RUN" if args.dry_run else "IMPORTED"
    print(
        f"{mode}: persons_created={result.persons_created}, "
        f"persons_existing={result.persons_existing}, orders_created={result.orders_created}, "
        f"orders_updated={result.orders_updated}, "
        f"memberships_created={result.memberships_created}, "
        f"memberships_updated={result.memberships_updated}, "
        f"memberships_skipped={result.memberships_skipped}"
    )


if __name__ == "__main__":
    asyncio.run(_main())
