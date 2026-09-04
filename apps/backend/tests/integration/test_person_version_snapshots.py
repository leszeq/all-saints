"""Integration coverage for complete, relation-aware person snapshots."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    serialize_person_snapshot,
)
from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography.models import (
    Beatification,
    Canonization,
    Gender,
    Patronage,
    Person,
    PersonOrder,
    PersonType,
    PublicationStatus,
)
from src.domain.sources.models import Bibliography, Image, PersonSource


@pytest.mark.asyncio
async def test_snapshot_contains_editable_person_relations(db_session: AsyncSession) -> None:
    person = Person(
        id=uuid.uuid4(),
        slug="sw-pelny-snapshot",
        canonical_name="Św. Pełny Snapshot",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
        version=1,
    )
    order = ReligiousOrder(slug="snapshot-order", name="Wspólnota Snapshot")
    bibliography = Bibliography(title="Źródło snapshotu")
    db_session.add_all([person, order, bibliography])
    await db_session.flush()

    patronage = Patronage(
        person_id=person.id,
        patronage_type="profession",
        name_pl="Redaktorzy danych",
        is_official=True,
    )
    image = Image(
        person_id=person.id,
        url="https://example.test/portrait.jpg",
        is_primary=True,
    )
    membership = PersonOrder(
        person_id=person.id,
        order_id=order.id,
        membership_type="founder",
        is_founder=True,
    )
    source = PersonSource(
        person_id=person.id,
        bibliography_id=bibliography.id,
        page_reference="s. 12",
        is_primary=True,
    )
    beatification = Beatification(
        person_id=person.id,
        beatification_year=2001,
    )
    canonization = Canonization(
        person_id=person.id,
        canonization_year=2005,
    )
    db_session.add_all(
        [patronage, image, membership, source, beatification, canonization]
    )

    snapshot = await serialize_person_snapshot(db_session, person)

    assert snapshot["_snapshot_schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert snapshot["id"] == str(person.id)
    assert snapshot["patronages"] == [
        {
            "id": str(patronage.id),
            "patronage_type": "profession",
            "name_pl": "Redaktorzy danych",
            "name_en": None,
            "description": None,
            "country_id": None,
            "is_official": True,
        }
    ]
    assert snapshot["images"][0]["url"] == "https://example.test/portrait.jpg"
    assert snapshot["images"][0]["is_primary"] is True
    assert snapshot["orders"] == [
        {
            "order_id": str(order.id),
            "entry_date": None,
            "exit_date": None,
            "is_founder": True,
            "membership_type": "founder",
            "notes": None,
        }
    ]
    assert snapshot["sources"][0]["bibliography_id"] == str(bibliography.id)
    assert snapshot["sources"][0]["page_reference"] == "s. 12"
    assert snapshot["beatification"]["beatification_year"] == 2001
    assert snapshot["canonization"]["canonization_year"] == 2005
