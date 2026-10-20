"""Unit coverage for public person-search reason and match projections."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.services.person_query_service import SearchPolicy
from src.domain.hagiography.models import Person, PersonName, PersonTranslation
from src.domain.hagiography.person_names import normalize_person_name


def _person(
    *,
    canonical_name: str = "Św. Jan Paweł II",
    canonical_name_en: str | None = "St. John Paul II",
    latin_name: str | None = "Sanctus Ioannes Paulus II",
) -> Person:
    return Person(
        id=uuid4(),
        slug="sw-jan-pawel-ii",
        canonical_name=canonical_name,
        canonical_name_en=canonical_name_en,
        latin_name=latin_name,
        person_type="saint",
        gender="male",
        aliases=[],
        translations=[],
    )


@pytest.mark.parametrize(
    ("query", "reason", "match"),
    [
        ("Sw. Jan Pawel II", "canonical_exact", "Św. Jan Paweł II"),
        ("St. John Paul II", "canonical_exact_en", "St. John Paul II"),
        (
            "Sanctus Ioannes Paulus II",
            "transliteration_exact",
            "Sanctus Ioannes Paulus II",
        ),
    ],
)
def test_exact_canonical_english_and_latin_names_are_explained(
    query: str, reason: str, match: str
) -> None:
    person = _person()

    assert SearchPolicy.reason_for_person(person, query) == reason
    assert SearchPolicy.match_for_person(person, query) == match


def test_alias_and_translation_matches_return_the_public_label() -> None:
    person = _person()
    person.aliases = [
        PersonName(
            id=uuid4(),
            person_id=person.id,
            value="Karol Wojtyła",
            normalized_value=normalize_person_name("Karol Wojtyła"),
            language_code="pl",
            kind="birth_name",
        )
    ]
    person.translations = [
        PersonTranslation(
            id=uuid4(),
            person_id=person.id,
            language_code="de",
            canonical_name="Johannes Paul II.",
        )
    ]

    assert SearchPolicy.reason_for_person(person, "Karol Wojtyla") == "alias_exact"
    assert SearchPolicy.match_for_person(person, "Karol Wojtyla") == "Karol Wojtyła"
    assert SearchPolicy.reason_for_person(person, "Johannes Paul II") == "translation_exact"
    assert SearchPolicy.match_for_person(person, "Johannes Paul II") == "Johannes Paul II."


def test_deleted_alias_and_translation_are_not_search_explanations() -> None:
    person = _person()
    deleted_at = datetime.now(UTC)
    person.aliases = [
        PersonName(
            id=uuid4(),
            person_id=person.id,
            value="Karol Wojtyła",
            normalized_value=normalize_person_name("Karol Wojtyła"),
            language_code="pl",
            kind="birth_name",
            deleted_at=deleted_at,
        )
    ]
    person.translations = [
        PersonTranslation(
            id=uuid4(),
            person_id=person.id,
            language_code="de",
            canonical_name="Johannes Paul II.",
            deleted_at=deleted_at,
        )
    ]

    assert SearchPolicy.reason_for_person(person, "Karol Wojtyla") == "fuzzy"
    assert SearchPolicy.match_for_person(person, "Karol Wojtyla") is None
    assert SearchPolicy.reason_for_person(person, "Johannes Paul II") == "fuzzy"
    assert SearchPolicy.match_for_person(person, "Johannes Paul II") is None


def test_typo_is_fuzzy_and_does_not_claim_an_exact_label() -> None:
    person = _person()

    assert SearchPolicy.reason_for_person(person, "Jan Pawel") == "fuzzy"
    assert SearchPolicy.match_for_person(person, "Jan Pawel") is None


def test_query_length_policy_trims_and_bounds_public_search_terms() -> None:
    assert SearchPolicy.normalize_query(None) is None
    assert SearchPolicy.normalize_query("  ") is None
    assert SearchPolicy.normalize_query(" a ") is None
    assert SearchPolicy.normalize_query("  Jan  ") == "Jan"
    assert SearchPolicy.normalize_query("x" * 250) == "x" * SearchPolicy.MAX_QUERY_LENGTH
