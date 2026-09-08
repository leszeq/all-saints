"""Unit tests for the religious communities catalogue dataset and schemas."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.infrastructure.db.import_religious_orders import read_dataset
from src.presentation.api.v1.orders.schemas import ReligiousOrderCreateSchema

DATASET = Path(__file__).parents[2] / "data" / "religious-orders"


def test_versioned_dataset_contains_orders_people_and_memberships() -> None:
    people, orders, memberships = read_dataset(DATASET)

    assert len(people) == 2
    assert len(orders) == 9
    assert len(memberships) == 12
    assert sum(order["is_featured"] == "true" for order in orders) == 3
    assert {order["community_type"] for order in orders} >= {
        "religious_order",
        "congregation",
        "monastic_family",
    }
    assert all(order["source_url"].startswith("https://") for order in orders)


def test_dataset_contains_society_of_jesus_with_ignatian_identity() -> None:
    _people, orders, _memberships = read_dataset(DATASET)

    jesuits = next(order for order in orders if order["slug"] == "jezuici")
    assert jesuits["name_la"] == "Societas Iesu"
    assert jesuits["abbreviation"] == "SJ"
    assert jesuits["spiritual_family"] == "ignacjanska"
    assert jesuits["founded_year"] == "1540"
    assert jesuits["founder_name"].startswith("św. Ignacy Loyola")
    assert jesuits["source_url"] == "https://www.jesuits.global/about-us/our-history/"


def test_dataset_distinguishes_spiritual_patron_from_membership() -> None:
    _people, _orders, memberships = read_dataset(DATASET)

    augustine = next(
        membership
        for membership in memberships
        if membership["person_slug"] == "sw-augustyn-z-hippony"
    )
    assert augustine["order_slug"] == "augustianie"
    assert augustine["membership_type"] == "spiritual_patron"
    assert augustine["is_founder"] == "false"


def test_order_slug_rejects_spaces_and_polish_characters() -> None:
    with pytest.raises(ValidationError):
        ReligiousOrderCreateSchema(slug="Siostry Miłosierdzia", name="Test")
