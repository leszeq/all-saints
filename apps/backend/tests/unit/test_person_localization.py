"""Language resolution policy for localized person content."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.services.person_localization import resolve_person_content
from src.domain.hagiography.models import Person, PersonTranslation


def _person() -> Person:
    person = Person(
        canonical_name="Św. Jan Testowy",
        canonical_name_en="St. John Test",
        slug="sw-jan-testowy",
        person_type="saint",
        gender="male",
        summary_pl="Polskie streszczenie",
        biography_pl="Polski biogram",
        summary_en="English summary",
        biography_en="English biography",
        prayers="Polska modlitwa",
        iconographic_attributes="Polskie atrybuty",
    )
    person.translations = []
    return person


def test_exact_translation_is_preferred_without_field_level_language_mixing() -> None:
    person = _person()
    person.translations = [
        PersonTranslation(
            person_id=person.id,
            language_code="fr",
            canonical_name="Saint Jean de Test",
            summary="Résumé français",
            biography=None,
            prayers=None,
            iconographic_attributes=None,
        )
    ]

    content = resolve_person_content(person, "FR")

    assert content.requested_locale == "fr"
    assert content.resolved_locale == "fr"
    assert content.fallback_used is False
    assert content.source == "translation"
    assert content.canonical_name == "Saint Jean de Test"
    assert content.summary == "Résumé français"
    assert content.biography is None
    assert content.prayers is None
    assert content.iconographic_attributes is None


def test_regional_locale_falls_back_to_primary_language_translation() -> None:
    person = _person()
    person.translations = [
        PersonTranslation(
            person_id=person.id,
            language_code="it",
            canonical_name="San Giovanni di Test",
            summary="Sommario italiano",
        )
    ]

    content = resolve_person_content(person, "it-IT")

    assert content.requested_locale == "it-it"
    assert content.resolved_locale == "it"
    assert content.fallback_used is True
    assert content.source == "translation"


def test_legacy_english_projection_does_not_fill_missing_fields_from_polish() -> None:
    content = resolve_person_content(_person(), "en")

    assert content.resolved_locale == "en"
    assert content.source == "legacy_person_columns"
    assert content.canonical_name == "St. John Test"
    assert content.summary == "English summary"
    assert content.biography == "English biography"
    assert content.prayers is None
    assert content.iconographic_attributes is None


def test_unknown_language_falls_back_to_legacy_polish_content() -> None:
    content = resolve_person_content(_person(), "de-DE")

    assert content.requested_locale == "de-de"
    assert content.resolved_locale == "pl"
    assert content.fallback_used is True
    assert content.source == "legacy_person_columns"
    assert content.canonical_name == "Św. Jan Testowy"
    assert content.prayers == "Polska modlitwa"


def test_active_translation_wins_and_soft_deleted_translation_is_ignored() -> None:
    person = _person()
    person.translations = [
        PersonTranslation(
            person_id=person.id,
            language_code="en",
            canonical_name="Deleted English name",
            deleted_at=datetime.now(UTC),
        ),
        PersonTranslation(
            person_id=person.id,
            language_code="pl",
            canonical_name="Święty Jan — wersja redakcyjna",
            summary="Streszczenie z tabeli tłumaczeń",
        ),
    ]

    english = resolve_person_content(person, "en")
    polish = resolve_person_content(person, "pl")

    assert english.source == "legacy_person_columns"
    assert english.canonical_name == "St. John Test"
    assert polish.source == "translation"
    assert polish.canonical_name == "Święty Jan — wersja redakcyjna"


def test_underscore_locale_is_normalized_to_bcp47_separator() -> None:
    person = _person()
    person.translations = [
        PersonTranslation(
            person_id=person.id,
            language_code="en-us",
            canonical_name="Saint John Test, US",
        )
    ]

    content = resolve_person_content(person, "EN_us")

    assert content.requested_locale == "en-us"
    assert content.resolved_locale == "en-us"
    assert content.fallback_used is False
    assert content.source == "translation"
