"""Stable, relation-aware snapshots used by person versioning and audit trails."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import (
    Beatification,
    Canonization,
    Patronage,
    Person,
    PersonName,
    PersonOrder,
    PersonVersion,
)
from src.domain.sources.models import Image, PersonSource

SNAPSHOT_SCHEMA_VERSION = 1

PATRONAGE_FIELDS = (
    "id",
    "patronage_type",
    "name_pl",
    "name_en",
    "description",
    "country_id",
    "is_official",
)
IMAGE_FIELDS = (
    "id",
    "url",
    "thumbnail_url",
    "storage_key",
    "title",
    "description",
    "image_type",
    "license",
    "photographer",
    "source_url",
    "year_created",
    "is_primary",
    "sort_order",
    "width_px",
    "height_px",
    "file_size_bytes",
    "mime_type",
)
ORDER_FIELDS = (
    "order_id",
    "entry_date",
    "exit_date",
    "is_founder",
    "membership_type",
    "notes",
)
SOURCE_FIELDS = (
    "id",
    "bibliography_id",
    "historical_source_id",
    "page_reference",
    "quote",
    "relevance_score",
    "is_primary",
    "notes",
)
ALIAS_FIELDS = (
    "id",
    "value",
    "normalized_value",
    "language_code",
    "kind",
)
BEATIFICATION_FIELDS = (
    "id",
    "pope_id",
    "beatification_date",
    "beatification_year",
    "place_id",
    "decree_number",
    "notes",
)
CANONIZATION_FIELDS = (
    "id",
    "pope_id",
    "canonization_date",
    "canonization_year",
    "place_id",
    "decree_number",
    "acta_reference",
    "notes",
)


def _fields(entity: object, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: getattr(entity, name) for name in names}


async def serialize_person_snapshot(
    db: AsyncSession,
    person: Person,
) -> dict[str, Any]:
    """Return a JSON-safe snapshot of the person and editable relations.

    The top-level scalar layout is intentionally preserved for compatibility with
    existing history consumers. ``_snapshot_schema_version`` allows a future
    migration without guessing which serializer produced an older version.
    """
    await db.flush()
    person_id = person.id

    patronages = list(
        (
            await db.execute(
                select(Patronage)
                .where(
                    Patronage.person_id == person_id,
                    Patronage.deleted_at.is_(None),
                )
                .order_by(Patronage.created_at.asc(), Patronage.id.asc())
            )
        )
        .scalars()
        .all()
    )
    images = list(
        (
            await db.execute(
                select(Image)
                .where(Image.person_id == person_id, Image.deleted_at.is_(None))
                .order_by(Image.sort_order.asc(), Image.created_at.asc(), Image.id.asc())
            )
        )
        .scalars()
        .all()
    )
    orders = list(
        (
            await db.execute(
                select(PersonOrder)
                .where(PersonOrder.person_id == person_id)
                .order_by(PersonOrder.order_id.asc())
            )
        )
        .scalars()
        .all()
    )
    sources = list(
        (
            await db.execute(
                select(PersonSource)
                .where(
                    PersonSource.person_id == person_id,
                    PersonSource.deleted_at.is_(None),
                )
                .order_by(PersonSource.created_at.asc(), PersonSource.id.asc())
            )
        )
        .scalars()
        .all()
    )
    aliases = list(
        (
            await db.execute(
                select(PersonName)
                .where(
                    PersonName.person_id == person_id,
                    PersonName.deleted_at.is_(None),
                )
                .order_by(PersonName.created_at.asc(), PersonName.id.asc())
            )
        )
        .scalars()
        .all()
    )
    beatification = (
        await db.execute(select(Beatification).where(Beatification.person_id == person_id))
    ).scalar_one_or_none()
    canonization = (
        await db.execute(select(Canonization).where(Canonization.person_id == person_id))
    ).scalar_one_or_none()

    snapshot = {
        **person.to_dict(),
        "_snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "patronages": [_fields(item, PATRONAGE_FIELDS) for item in patronages],
        "images": [_fields(item, IMAGE_FIELDS) for item in images],
        "orders": [_fields(item, ORDER_FIELDS) for item in orders],
        "sources": [_fields(item, SOURCE_FIELDS) for item in sources],
        "aliases": [_fields(item, ALIAS_FIELDS) for item in aliases],
        "beatification": (
            _fields(beatification, BEATIFICATION_FIELDS) if beatification is not None else None
        ),
        "canonization": (
            _fields(canonization, CANONIZATION_FIELDS) if canonization is not None else None
        ),
    }
    return cast(dict[str, Any], jsonable_encoder(snapshot))


async def lock_person_for_snapshot(
    db: AsyncSession,
    person_id: uuid.UUID,
) -> Person | None:
    """Lock one active person before a relation mutation and version increment."""
    return (
        await db.execute(
            select(Person)
            .where(Person.id == person_id, Person.deleted_at.is_(None))
            .with_for_update()
        )
    ).scalar_one_or_none()


async def append_relation_version(
    db: AsyncSession,
    person: Person,
    *,
    previous_snapshot: dict[str, Any],
    changed_by_id: uuid.UUID | None,
    change_summary: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Increment the person revision and return before/after relation snapshots."""
    person.version += 1
    person.updated_at = datetime.now(UTC)
    await db.flush()
    current_snapshot = await serialize_person_snapshot(db, person)

    db.add(
        PersonVersion(
            person_id=person.id,
            version_number=person.version,
            snapshot=current_snapshot,
            changed_by_id=changed_by_id,
            changed_at=datetime.now(UTC),
            change_summary=change_summary,
        )
    )
    return previous_snapshot, current_snapshot
