"""Unit coverage for deterministic legacy-content translation backfill."""

from __future__ import annotations

import uuid

from src.application.services.person_translation_backfill import (
    PersonTranslationBackfillConflict,
    PersonTranslationBackfillResult,
    legacy_translation_payloads,
)
from src.domain.hagiography.models import Person


def test_legacy_payloads_keep_language_boundaries() -> None:
    person = Person(
        slug="sw-testowy",
        canonical_name="Św. Testowy",
        canonical_name_en="St. Test",
        summary_pl="Polskie streszczenie",
        summary_en="English summary",
        biography_pl="Polski biogram",
        biography_en="English biography",
        prayers="Polska modlitwa",
        iconographic_attributes="Polskie atrybuty",
        person_type="saint",
        gender="unknown",
    )

    payloads = legacy_translation_payloads(person)

    assert payloads["pl"] == {
        "canonical_name": "Św. Testowy",
        "summary": "Polskie streszczenie",
        "biography": "Polski biogram",
        "prayers": "Polska modlitwa",
        "iconographic_attributes": "Polskie atrybuty",
    }
    assert payloads["en"] == {
        "canonical_name": "St. Test",
        "summary": "English summary",
        "biography": "English biography",
        "prayers": None,
        "iconographic_attributes": None,
    }


def test_empty_english_legacy_projection_is_not_a_backfill_candidate() -> None:
    person = Person(
        slug="sw-tylko-polski",
        canonical_name="Św. Tylko Polski",
        canonical_name_en="   ",
        person_type="saint",
        gender="unknown",
    )

    assert set(legacy_translation_payloads(person)) == {"pl"}


def test_backfill_report_is_json_safe_and_explicit_about_mode() -> None:
    person_id = uuid.uuid4()
    result = PersonTranslationBackfillResult(
        apply=False,
        scanned_persons=2,
        candidate_translations=1,
        conflicts=[
            PersonTranslationBackfillConflict(
                person_id=person_id,
                slug="sw-konflikt",
                locale="pl",
                reason="content_mismatch",
                differing_fields=("canonical_name",),
                existing_language_code="pl",
            )
        ],
    )

    report = result.to_dict()

    assert report["mode"] == "dry-run"
    assert report["conflict_count"] == 1
    assert report["conflicts"] == [
        {
            "person_id": str(person_id),
            "slug": "sw-konflikt",
            "locale": "pl",
            "reason": "content_mismatch",
            "differing_fields": ["canonical_name"],
            "existing_language_code": "pl",
        }
    ]
