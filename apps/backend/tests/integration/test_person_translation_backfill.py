"""PostgreSQL coverage for the idempotent translation backfill."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_translation_backfill import (
    PersonTranslationBackfillService,
)
from src.domain.hagiography.models import (
    Gender,
    Person,
    PersonTranslation,
    PersonType,
    PersonVersion,
    PublicationStatus,
)


def _person(*, slug: str, name: str, name_en: str | None = None) -> Person:
    return Person(
        slug=slug,
        canonical_name=name,
        canonical_name_en=name_en,
        summary_pl=f"Polskie streszczenie: {name}",
        summary_en=f"English summary: {name_en}" if name_en else None,
        biography_pl=f"Polski biogram: {name}",
        biography_en=f"English biography: {name_en}" if name_en else None,
        prayers="Polska modlitwa",
        iconographic_attributes="Księga",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.UNKNOWN.value,
        version=7,
    )


@pytest.mark.asyncio
async def test_backfill_is_dry_by_default_applies_once_and_does_not_version_content(
    db_session: AsyncSession,
) -> None:
    bilingual = _person(
        slug="sw-dwujezyczny",
        name="Św. Dwujęzyczny",
        name_en="St. Bilingual",
    )
    polish_only = _person(slug="sw-polski", name="Św. Polski")
    db_session.add_all([bilingual, polish_only])
    await db_session.flush()
    service = PersonTranslationBackfillService(db_session)

    dry_run = await service.run()

    assert dry_run.apply is False
    assert dry_run.scanned_persons == 2
    assert dry_run.candidate_translations == 3
    assert dry_run.created_translations == 0
    assert dry_run.skipped_empty_locales == 1
    assert dry_run.conflicts == []
    assert (await db_session.scalar(select(func.count()).select_from(PersonTranslation))) == 0

    applied = await service.run(apply=True, batch_size=1)

    assert applied.candidate_translations == 3
    assert applied.created_translations == 3
    translations = list(
        (
            await db_session.execute(
                select(PersonTranslation).order_by(
                    PersonTranslation.person_id,
                    PersonTranslation.language_code,
                )
            )
        )
        .scalars()
        .all()
    )
    assert {(item.person_id, item.language_code) for item in translations} == {
        (bilingual.id, "pl"),
        (bilingual.id, "en"),
        (polish_only.id, "pl"),
    }
    english = next(item for item in translations if item.language_code == "en")
    assert english.prayers is None
    assert english.iconographic_attributes is None
    assert english.translated_by_id is None
    assert bilingual.version == 7
    assert (await db_session.scalar(select(func.count()).select_from(PersonVersion))) == 0

    repeated = await service.run(apply=True)

    assert repeated.candidate_translations == 0
    assert repeated.created_translations == 0
    assert repeated.existing_unchanged == 3
    assert repeated.conflicts == []


@pytest.mark.asyncio
async def test_backfill_reports_conflicts_without_overwriting_editorial_rows(
    db_session: AsyncSession,
) -> None:
    mismatch = _person(
        slug="sw-rozbieznosc",
        name="Św. Wartość Legacy",
        name_en="St. Legacy Value",
    )
    deleted = _person(
        slug="sw-usuniete-tlumaczenie",
        name="Św. Usunięte Tłumaczenie",
        name_en="St. Deleted Translation",
    )
    non_normalized = _person(
        slug="sw-nienormalny-jezyk",
        name="Św. Nienormalny Język",
    )
    db_session.add_all([mismatch, deleted, non_normalized])
    await db_session.flush()
    db_session.add_all(
        [
            PersonTranslation(
                person_id=mismatch.id,
                language_code="pl",
                canonical_name="Św. Wartość Redakcyjna",
                summary=mismatch.summary_pl,
                biography=mismatch.biography_pl,
                prayers=mismatch.prayers,
                iconographic_attributes=mismatch.iconographic_attributes,
            ),
            PersonTranslation(
                person_id=deleted.id,
                language_code="en",
                canonical_name=deleted.canonical_name_en,
                deleted_at=datetime.now(UTC),
            ),
            PersonTranslation(
                person_id=non_normalized.id,
                language_code="PL",
                canonical_name=non_normalized.canonical_name,
            ),
        ]
    )
    await db_session.flush()

    result = await PersonTranslationBackfillService(db_session).run(apply=True)

    conflicts = {(item.slug, item.locale): item for item in result.conflicts}
    assert conflicts[(mismatch.slug, "pl")].reason == "content_mismatch"
    assert conflicts[(mismatch.slug, "pl")].differing_fields == ("canonical_name",)
    assert conflicts[(deleted.slug, "en")].reason == "soft_deleted_target"
    assert conflicts[(non_normalized.slug, "pl")].reason == "non_normalized_locale"
    assert result.created_translations == 2

    editorial_polish = (
        await db_session.execute(
            select(PersonTranslation).where(
                PersonTranslation.person_id == mismatch.id,
                PersonTranslation.language_code == "pl",
            )
        )
    ).scalar_one()
    assert editorial_polish.canonical_name == "Św. Wartość Redakcyjna"
