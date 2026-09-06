"""Deterministic locale resolution for person editorial content."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from src.application.person_models import PersonLocalizedContentSchema
from src.domain.hagiography.models import Person, PersonTranslation

DEFAULT_CONTENT_LOCALE = "pl"
LEGACY_CONTENT_LOCALES = frozenset({"pl", "en"})

ContentSource = Literal["translation", "legacy_person_columns"]
ContentValues = tuple[str | None, str | None, str | None, str | None, str | None]


def normalize_content_locale(value: str | None) -> str:
    """Normalize a BCP 47-like language tag for storage and comparison."""
    normalized = (value or DEFAULT_CONTENT_LOCALE).strip().lower().replace("_", "-")
    return normalized or DEFAULT_CONTENT_LOCALE


def content_locale_fallbacks(value: str | None) -> tuple[str, ...]:
    """Return exact, primary-language and Polish locale candidates without duplicates."""
    requested = normalize_content_locale(value)
    candidates = [requested]
    primary_language = requested.split("-", maxsplit=1)[0]
    if primary_language not in candidates:
        candidates.append(primary_language)
    if DEFAULT_CONTENT_LOCALE not in candidates:
        candidates.append(DEFAULT_CONTENT_LOCALE)
    return tuple(candidates)


def _has_content(values: Iterable[str | None]) -> bool:
    return any(value is not None and bool(value.strip()) for value in values)


def _translation_values(translation: PersonTranslation) -> ContentValues:
    return (
        translation.canonical_name,
        translation.summary,
        translation.biography,
        translation.prayers,
        translation.iconographic_attributes,
    )


def _legacy_polish_values(person: Person) -> ContentValues:
    return (
        person.canonical_name,
        person.summary_pl,
        person.biography_pl,
        person.prayers,
        person.iconographic_attributes,
    )


def _legacy_values(person: Person, locale: str) -> ContentValues | None:
    if locale == "en":
        values: ContentValues = (
            person.canonical_name_en,
            person.summary_en,
            person.biography_en,
            None,
            None,
        )
        return values if _has_content(values) else None
    if locale == DEFAULT_CONTENT_LOCALE:
        return _legacy_polish_values(person)
    return None


def _localized_content(
    *,
    requested_locale: str,
    resolved_locale: str,
    source: ContentSource,
    values: ContentValues,
) -> PersonLocalizedContentSchema:
    canonical_name, summary, biography, prayers, iconographic_attributes = values
    return PersonLocalizedContentSchema(
        requested_locale=requested_locale,
        resolved_locale=resolved_locale,
        fallback_used=resolved_locale != requested_locale,
        source=source,
        canonical_name=canonical_name,
        summary=summary,
        biography=biography,
        prayers=prayers,
        iconographic_attributes=iconographic_attributes,
    )


def resolve_person_content(person: Person, locale: str | None) -> PersonLocalizedContentSchema:
    """Resolve one non-mixed content record using translation, legacy, then Polish fallback."""
    requested_locale = normalize_content_locale(locale)
    active_translations: dict[str, PersonTranslation] = {}
    for translation in person.translations:
        if translation.deleted_at is not None:
            continue
        language_code = normalize_content_locale(translation.language_code)
        active_translations.setdefault(language_code, translation)

    for candidate in content_locale_fallbacks(requested_locale):
        candidate_translation = active_translations.get(candidate)
        if candidate_translation is not None:
            values = _translation_values(candidate_translation)
            if _has_content(values):
                return _localized_content(
                    requested_locale=requested_locale,
                    resolved_locale=candidate,
                    source="translation",
                    values=values,
                )

        if candidate in LEGACY_CONTENT_LOCALES:
            legacy_values = _legacy_values(person, candidate)
            if legacy_values is not None:
                return _localized_content(
                    requested_locale=requested_locale,
                    resolved_locale=candidate,
                    source="legacy_person_columns",
                    values=legacy_values,
                )

    # Person.canonical_name is required, so the Polish legacy projection is always available.
    return _localized_content(
        requested_locale=requested_locale,
        resolved_locale=DEFAULT_CONTENT_LOCALE,
        source="legacy_person_columns",
        values=_legacy_polish_values(person),
    )
