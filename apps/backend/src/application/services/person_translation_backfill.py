"""Idempotent migration from legacy person columns to translation rows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.person_translations import TRANSLATED_CONTENT_FIELDS
from src.application.services.person_localization import normalize_content_locale
from src.domain.hagiography.models import Person, PersonTranslation

TranslationPayload = dict[str, str | None]
BackfillConflictReason = Literal[
    "content_mismatch",
    "soft_deleted_target",
    "non_normalized_locale",
    "duplicate_normalized_locale",
]


def _legacy_value(value: str | None) -> str | None:
    """Keep non-empty legacy text byte-for-byte while treating blank text as absent."""
    if value is None or not value.strip():
        return None
    return value


def legacy_translation_payloads(person: Person) -> dict[str, TranslationPayload]:
    """Project legacy columns without mixing Polish-only fields into English."""
    polish: TranslationPayload = {
        "canonical_name": _legacy_value(person.canonical_name),
        "summary": _legacy_value(person.summary_pl),
        "biography": _legacy_value(person.biography_pl),
        "prayers": _legacy_value(person.prayers),
        "iconographic_attributes": _legacy_value(person.iconographic_attributes),
    }
    english: TranslationPayload = {
        "canonical_name": _legacy_value(person.canonical_name_en),
        "summary": _legacy_value(person.summary_en),
        "biography": _legacy_value(person.biography_en),
        "prayers": None,
        "iconographic_attributes": None,
    }
    payloads = {"pl": polish}
    if any(english.values()):
        payloads["en"] = english
    return payloads


@dataclass(frozen=True, slots=True)
class PersonTranslationBackfillConflict:
    """One locale that requires an explicit editorial decision."""

    person_id: uuid.UUID
    slug: str
    locale: str
    reason: BackfillConflictReason
    differing_fields: tuple[str, ...] = ()
    existing_language_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "person_id": str(self.person_id),
            "slug": self.slug,
            "locale": self.locale,
            "reason": self.reason,
            "differing_fields": list(self.differing_fields),
            "existing_language_code": self.existing_language_code,
        }


@dataclass(slots=True)
class PersonTranslationBackfillResult:
    """Counters and conflicts emitted by one complete backfill scan."""

    apply: bool
    scanned_persons: int = 0
    candidate_translations: int = 0
    created_translations: int = 0
    existing_unchanged: int = 0
    skipped_empty_locales: int = 0
    conflicts: list[PersonTranslationBackfillConflict] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": "apply" if self.apply else "dry-run",
            "scanned_persons": self.scanned_persons,
            "candidate_translations": self.candidate_translations,
            "created_translations": self.created_translations,
            "existing_unchanged": self.existing_unchanged,
            "skipped_empty_locales": self.skipped_empty_locales,
            "conflict_count": len(self.conflicts),
            "conflicts": [conflict.to_dict() for conflict in self.conflicts],
        }


def _comparable(value: str | None) -> str | None:
    return value.strip() if value is not None and value.strip() else None


def _differing_source_fields(
    translation: PersonTranslation,
    payload: TranslationPayload,
) -> tuple[str, ...]:
    """Compare only legacy fields that contain data; extra translated text is valid."""
    return tuple(
        field_name
        for field_name in TRANSLATED_CONTENT_FIELDS
        if _comparable(payload[field_name]) is not None
        and _comparable(getattr(translation, field_name)) != _comparable(payload[field_name])
    )


class PersonTranslationBackfillService:
    """Scan all people and copy only unambiguous missing locale projections."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _group_translations(
        translations: list[PersonTranslation],
    ) -> dict[tuple[uuid.UUID, str], list[PersonTranslation]]:
        grouped: dict[tuple[uuid.UUID, str], list[PersonTranslation]] = {}
        for translation in translations:
            key = (
                translation.person_id,
                normalize_content_locale(translation.language_code),
            )
            grouped.setdefault(key, []).append(translation)
        return grouped

    @staticmethod
    def _conflict(
        person: Person,
        locale: str,
        translations: list[PersonTranslation],
        payload: TranslationPayload,
    ) -> PersonTranslationBackfillConflict | None:
        if len(translations) > 1:
            return PersonTranslationBackfillConflict(
                person_id=person.id,
                slug=person.slug,
                locale=locale,
                reason="duplicate_normalized_locale",
                existing_language_code=", ".join(
                    sorted(translation.language_code for translation in translations)
                ),
            )

        translation = translations[0]
        if translation.language_code != locale:
            return PersonTranslationBackfillConflict(
                person_id=person.id,
                slug=person.slug,
                locale=locale,
                reason="non_normalized_locale",
                existing_language_code=translation.language_code,
            )
        if translation.deleted_at is not None:
            return PersonTranslationBackfillConflict(
                person_id=person.id,
                slug=person.slug,
                locale=locale,
                reason="soft_deleted_target",
                existing_language_code=translation.language_code,
            )

        differing_fields = _differing_source_fields(translation, payload)
        if differing_fields:
            return PersonTranslationBackfillConflict(
                person_id=person.id,
                slug=person.slug,
                locale=locale,
                reason="content_mismatch",
                differing_fields=differing_fields,
                existing_language_code=translation.language_code,
            )
        return None

    async def run(
        self,
        *,
        apply: bool = False,
        batch_size: int = 500,
    ) -> PersonTranslationBackfillResult:
        """Analyze by default; insert missing rows only when apply is explicit."""
        if batch_size < 1:
            raise ValueError("batch_size musi być dodatni")

        result = PersonTranslationBackfillResult(apply=apply)
        last_person_id: uuid.UUID | None = None
        while True:
            person_query = select(Person).order_by(Person.id.asc()).limit(batch_size)
            if last_person_id is not None:
                person_query = person_query.where(Person.id > last_person_id)
            people = list((await self.db.execute(person_query)).scalars().all())
            if not people:
                break

            person_ids = [person.id for person in people]
            translations = list(
                (
                    await self.db.execute(
                        select(PersonTranslation)
                        .where(PersonTranslation.person_id.in_(person_ids))
                        .order_by(
                            PersonTranslation.person_id.asc(),
                            PersonTranslation.language_code.asc(),
                            PersonTranslation.id.asc(),
                        )
                    )
                )
                .scalars()
                .all()
            )
            grouped = self._group_translations(translations)

            for person in people:
                result.scanned_persons += 1
                payloads = legacy_translation_payloads(person)
                for locale in ("pl", "en"):
                    payload = payloads.get(locale)
                    if payload is None:
                        result.skipped_empty_locales += 1
                        continue

                    current = grouped.get((person.id, locale), [])
                    if current:
                        conflict = self._conflict(person, locale, current, payload)
                        if conflict is not None:
                            result.conflicts.append(conflict)
                        else:
                            result.existing_unchanged += 1
                        continue

                    result.candidate_translations += 1
                    if apply:
                        self.db.add(
                            PersonTranslation(
                                person_id=person.id,
                                language_code=locale,
                                translated_by_id=None,
                                **payload,
                            )
                        )
                        result.created_translations += 1

            if apply:
                await self.db.flush()
            last_person_id = people[-1].id

        return result
