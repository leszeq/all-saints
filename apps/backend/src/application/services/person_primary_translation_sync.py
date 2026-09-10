"""Keep legacy editor fields and active primary translations consistent."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.hagiography.models import Person, PersonTranslation

PRIMARY_TRANSLATION_FIELD_MAP: dict[str, dict[str, str]] = {
    "pl": {
        "canonical_name": "canonical_name",
        "summary_pl": "summary",
        "biography_pl": "biography",
        "prayers": "prayers",
        "iconographic_attributes": "iconographic_attributes",
    },
    "en": {
        "canonical_name_en": "canonical_name",
        "summary_en": "summary",
        "biography_en": "biography",
    },
}


class PersonPrimaryTranslationSynchronizer:
    """Update existing ``pl``/``en`` rows after legacy profile edits.

    Public responses prefer an active ``PersonTranslation`` over the transitional
    legacy columns on ``Person``. Until the admin form writes translations
    directly, every edited primary-locale field therefore has to update the
    corresponding active translation in the same transaction. Missing rows are
    intentionally not created because localization already falls back to the
    legacy fields.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def sync_existing(
        self,
        person: Person,
        *,
        changed_fields: set[str],
        user_id: uuid.UUID | None,
    ) -> tuple[str, ...]:
        affected_locales = {
            locale
            for locale, field_map in PRIMARY_TRANSLATION_FIELD_MAP.items()
            if changed_fields.intersection(field_map)
        }
        if not affected_locales:
            return ()

        translations = list(
            (
                await self._db.execute(
                    select(PersonTranslation)
                    .where(
                        PersonTranslation.person_id == person.id,
                        PersonTranslation.language_code.in_(affected_locales),
                        PersonTranslation.deleted_at.is_(None),
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        synchronized: list[str] = []
        changed_at = datetime.now(UTC)
        for translation in translations:
            field_map = PRIMARY_TRANSLATION_FIELD_MAP[translation.language_code]
            row_changed = False
            for person_field in changed_fields.intersection(field_map):
                translation_field = field_map[person_field]
                value = getattr(person, person_field)
                if getattr(translation, translation_field) == value:
                    continue
                setattr(translation, translation_field, value)
                row_changed = True
            if not row_changed:
                continue
            translation.version += 1
            translation.updated_at = changed_at
            translation.translated_by_id = user_id
            synchronized.append(translation.language_code)

        return tuple(sorted(synchronized))
