"""Integration coverage for isolated publication revision drafts."""

import runpy
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.persons import PersonCreateSchema, PersonUpdateSchema
from src.application.services.audit_service import AuditContext
from src.application.services.person_service import PersonService, PersonVersionConflictError
from src.application.services.publication_revision_service import (
    PublicationRevisionConflictError,
    PublicationRevisionPayloadError,
    PublicationRevisionService,
    PublicationRevisionStateError,
    PublicationRevisionVersionConflictError,
)
from src.domain.hagiography.models import (
    Beatification,
    Canonization,
    Patronage,
    Person,
    PersonName,
    PublicationRevision,
    PublicationRevisionStatus,
    PublicationStatus,
)
from src.domain.identity.models import AuditLog
from src.domain.sources.models import Image

_BACKFILL_MIGRATION = runpy.run_path(
    str(Path(__file__).parents[2] / "alembic/versions/0029_backfill_published_revision_pointer.py")
)


async def _published_person(db_session: AsyncSession) -> Person:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Rewizja Testowa",
            summary_pl="Aktualny opis publiczny",
            person_type="saint",
            gender="male",
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    await db_session.flush()
    await db_session.refresh(person)
    return person


@pytest.mark.asyncio
async def test_create_draft_revision_keeps_live_person_unchanged(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    base_version = person.version

    revision = await PublicationRevisionService(db_session).create_draft(
        person.id,
        expected_version=base_version,
        author_id=None,
        audit_context=AuditContext(),
        change_summary="Przygotowanie aktualizacji biogramu",
    )

    assert revision.revision_number == 1
    assert revision.status == PublicationRevisionStatus.DRAFT.value
    assert revision.base_version == base_version
    assert revision.change_summary == "Przygotowanie aktualizacji biogramu"
    assert revision.payload["canonical_name"] == person.canonical_name
    assert revision.payload["summary_pl"] == "Aktualny opis publiczny"
    assert person.version == base_version
    assert person.summary_pl == "Aktualny opis publiczny"

    audit_log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.resource_type == "person_revisions",
            AuditLog.resource_id == revision.id,
        )
    )
    assert audit_log is not None
    assert audit_log.new_value == {
        "person_id": str(person.id),
        "revision_number": 1,
        "base_version": base_version,
        "status": PublicationRevisionStatus.DRAFT.value,
    }


@pytest.mark.asyncio
async def test_get_active_revision_returns_draft_and_then_review_revision(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )

    active = await service.get_active_revision(person.id)
    assert active is not None
    assert active.id == revision.id
    assert active.status == PublicationRevisionStatus.DRAFT.value

    submitted = await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )
    active = await service.get_active_revision(person.id)
    assert active is not None
    assert active.id == submitted.id
    assert active.status == PublicationRevisionStatus.REVIEW.value


@pytest.mark.asyncio
async def test_create_draft_revision_rejects_stale_version_and_duplicate_draft(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )

    with pytest.raises(PersonVersionConflictError):
        await service.create_draft(
            person.id,
            expected_version=person.version - 1,
            author_id=None,
        )

    with pytest.raises(PublicationRevisionConflictError):
        await service.create_draft(
            person.id,
            expected_version=person.version,
            author_id=None,
        )

    assert (
        await db_session.scalar(
            select(PublicationRevision).where(PublicationRevision.person_id == person.id)
        )
    ) is not None


@pytest.mark.asyncio
async def test_create_draft_revision_requires_published_person(
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Szkic bez rewizji",
            person_type="saint",
            gender="male",
        )
    )

    with pytest.raises(PublicationRevisionStateError):
        await PublicationRevisionService(db_session).create_draft(
            person.id,
            expected_version=person.version,
            author_id=None,
        )


@pytest.mark.asyncio
async def test_update_draft_revision_versions_scalar_changes_and_audits_them(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )

    updated = await service.update_draft(
        revision.id,
        expected_version=revision.version,
        changes={"summary_pl": "Nowy opis w izolowanym draftcie"},
        author_id=None,
        audit_context=AuditContext(),
        change_summary="Korekta streszczenia",
    )

    assert updated.version == 2
    assert updated.payload["summary_pl"] == "Nowy opis w izolowanym draftcie"
    assert updated.change_summary == "Korekta streszczenia"
    assert person.summary_pl == "Aktualny opis publiczny"
    assert person.version == 1

    audit_log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.resource_type == "person_revisions",
            AuditLog.resource_id == revision.id,
            AuditLog.action == "update",
        )
    )
    assert audit_log is not None
    assert audit_log.old_value["version"] == 1
    assert audit_log.new_value["version"] == 2
    assert audit_log.new_value["changes"]["summary_pl"] == (
        "Nowy opis w izolowanym draftcie"
    )

    with pytest.raises(PublicationRevisionVersionConflictError):
        await service.update_draft(
            revision.id,
            expected_version=1,
            changes={"summary_pl": "Próba na starej wersji"},
            author_id=None,
        )


@pytest.mark.asyncio
async def test_update_draft_revision_stages_editable_relations_without_live_mutation(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )

    updated = await service.update_draft(
        revision.id,
        expected_version=revision.version,
        changes={
            "avatar": {
                "url": "https://example.org/rewizja.jpg",
                "title": "Portret rewizji",
                "license": "public_domain",
            },
            "aliases": [
                {"value": "Rewizja Testowa", "language_code": "pl", "kind": "alias"}
            ],
            "patronages": [
                {
                    "patronage_type": "profession",
                    "name_pl": "redaktorów",
                    "name_en": "editors",
                    "is_official": True,
                }
            ],
            "beatification": {"beatification_year": 1953},
            "canonization": {"canonization_date": "1983-06-02", "canonization_year": 1983},
        },
        author_id=None,
    )

    assert updated.payload["avatar"]["url"] == "https://example.org/rewizja.jpg"
    assert updated.payload["aliases"][0]["value"] == "Rewizja Testowa"
    assert updated.payload["patronages"][0]["name_pl"] == "redaktorów"
    assert updated.payload["beatification"] == {"beatification_year": 1953}
    assert updated.payload["canonization"] == {
        "canonization_date": "1983-06-02",
        "canonization_year": 1983,
    }
    assert updated.payload["_edited_relation_fields"] == [
        "aliases",
        "avatar",
        "beatification",
        "canonization",
        "patronages",
    ]

    assert (
        await db_session.scalars(select(PersonName).where(PersonName.person_id == person.id))
    ).all() == []
    assert (
        await db_session.scalars(select(Patronage).where(Patronage.person_id == person.id))
    ).all() == []
    assert (
        await db_session.scalars(select(Image).where(Image.person_id == person.id))
    ).all() == []
    assert (
        await db_session.scalars(
            select(Beatification).where(Beatification.person_id == person.id)
        )
    ).all() == []
    assert (
        await db_session.scalars(select(Canonization).where(Canonization.person_id == person.id))
    ).all() == []


@pytest.mark.asyncio
async def test_publish_revision_applies_editable_relations_atomically(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    revision = await service.update_draft(
        revision.id,
        expected_version=revision.version,
        changes={
            "avatar": {
                "url": "https://example.org/rewizja.jpg",
                "title": "Portret rewizji",
                "license": "public_domain",
            },
            "aliases": [{"value": "Rewizja Testowa", "language_code": "pl"}],
            "patronages": [
                {"patronage_type": "profession", "name_pl": "redaktorów"}
            ],
            "beatification": {"beatification_year": 1953},
            "canonization": {"canonization_year": 1983},
        },
        author_id=None,
    )
    submitted = await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )

    await service.publish(
        revision.id,
        expected_version=submitted.version,
        author_id=None,
    )

    alias = await db_session.scalar(
        select(PersonName).where(PersonName.person_id == person.id)
    )
    patronage = await db_session.scalar(
        select(Patronage).where(Patronage.person_id == person.id)
    )
    image = await db_session.scalar(select(Image).where(Image.person_id == person.id))
    beatification = await db_session.scalar(
        select(Beatification).where(Beatification.person_id == person.id)
    )
    canonization = await db_session.scalar(
        select(Canonization).where(Canonization.person_id == person.id)
    )

    assert alias is not None
    assert alias.value == "Rewizja Testowa"
    assert patronage is not None
    assert patronage.name_pl == "redaktorów"
    assert image is not None
    assert image.url == "https://example.org/rewizja.jpg"
    assert image.is_primary is True
    assert beatification is not None
    assert beatification.beatification_year == 1953
    assert canonization is not None
    assert canonization.canonization_year == 1983


@pytest.mark.asyncio
async def test_scalar_revision_publish_preserves_relations_not_edited_in_draft(
    db_session: AsyncSession,
) -> None:
    person = await PersonService(db_session).create_person(
        PersonCreateSchema(
            canonical_name="Św. Rewizja z relacjami",
            person_type="saint",
            gender="male",
            avatar={
                "url": "https://example.org/oryginal.jpg",
                "title": "Oryginalny portret",
                "license": "public_domain",
            },
            aliases=[{"value": "Oryginalny alias", "language_code": "pl"}],
            patronages=[{"patronage_type": "city", "name_pl": "Krakowa"}],
            beatification={"beatification_year": 1950},
            canonization={"canonization_year": 1960},
        )
    )
    person.status = PublicationStatus.PUBLISHED.value
    await db_session.flush()
    await db_session.refresh(person)

    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    revision = await service.update_draft(
        revision.id,
        expected_version=revision.version,
        changes={"summary_pl": "Zmieniony opis"},
        author_id=None,
    )
    submitted = await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )
    await service.publish(
        revision.id,
        expected_version=submitted.version,
        author_id=None,
    )

    assert (
        await db_session.scalar(
            select(PersonName).where(PersonName.person_id == person.id)
        )
    ).value == "Oryginalny alias"
    assert (
        await db_session.scalar(select(Patronage).where(Patronage.person_id == person.id))
    ).name_pl == "Krakowa"
    assert (
        await db_session.scalar(select(Image).where(Image.person_id == person.id))
    ).url == "https://example.org/oryginal.jpg"
    assert (
        await db_session.scalar(
            select(Beatification).where(Beatification.person_id == person.id)
        )
    ).beatification_year == 1950
    assert (
        await db_session.scalar(select(Canonization).where(Canonization.person_id == person.id))
    ).canonization_year == 1960


@pytest.mark.asyncio
async def test_update_draft_revision_exposes_field_validation_details(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )

    with pytest.raises(PublicationRevisionPayloadError) as error:
        await service.update_draft(
            revision.id,
            expected_version=revision.version,
            changes={"status": "published"},
            author_id=None,
        )

    assert error.value.details == [
        {
            "field": "changes.status",
            "message": "Pole jest zarządzane przez workflow rewizji",
            "type": "revision_field_forbidden",
        }
    ]


@pytest.mark.asyncio
async def test_submit_and_publish_revision_updates_live_person_atomically(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    revision = await service.update_draft(
        revision.id,
        expected_version=revision.version,
        changes={"summary_pl": "Opis zatwierdzony przez recenzenta"},
        author_id=None,
    )

    submitted = await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
        note="Gotowe do recenzji",
    )
    assert submitted.status == PublicationRevisionStatus.REVIEW.value
    assert submitted.version == 3
    assert person.summary_pl == "Aktualny opis publiczny"

    published = await service.publish(
        revision.id,
        expected_version=submitted.version,
        author_id=None,
        audit_context=AuditContext(),
        note="Publikacja po akceptacji",
    )

    await db_session.refresh(person)
    assert published.status == PublicationRevisionStatus.PUBLISHED.value
    assert published.version == 4
    assert person.status == PublicationStatus.PUBLISHED.value
    assert person.version == 2
    assert person.summary_pl == "Opis zatwierdzony przez recenzenta"
    assert person.published_revision_id == published.id

    audit_log = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.resource_type == "person_revisions",
            AuditLog.resource_id == revision.id,
            AuditLog.action == "publish",
        )
    )
    assert audit_log is not None
    assert audit_log.new_value["person_version"] == person.version


@pytest.mark.asyncio
async def test_legacy_published_update_clears_selected_revision_pointer(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    revision_service = PublicationRevisionService(db_session)
    revision = await revision_service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    submitted = await revision_service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )
    await revision_service.publish(
        revision.id,
        expected_version=submitted.version,
        author_id=None,
    )
    await db_session.refresh(person)
    assert person.published_revision_id == revision.id

    await PersonService(db_session).update_person(
        person,
        PersonUpdateSchema(
            summary_pl="Starsza ścieżka edycji",
            expected_version=person.version,
        ),
        allow_published_update=True,
    )

    await db_session.refresh(person)
    assert person.published_revision_id is None


@pytest.mark.asyncio
async def test_legacy_published_revision_backfill_is_idempotent(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)

    for statement_name in (
        "BACKFILL_LEGACY_PUBLISHED_REVISIONS_SQL",
        "SET_BACKFILLED_POINTERS_SQL",
    ):
        await db_session.execute(text(_BACKFILL_MIGRATION[statement_name]))
    await db_session.commit()
    await db_session.refresh(person)

    revision = await db_session.scalar(
        select(PublicationRevision).where(PublicationRevision.person_id == person.id)
    )
    assert revision is not None
    assert revision.status == PublicationRevisionStatus.PUBLISHED.value
    assert revision.revision_number == 1
    assert person.published_revision_id == revision.id
    assert revision.payload["_snapshot_schema_version"] == 2
    assert revision.payload["canonical_name"] == person.canonical_name
    assert revision.payload["summary_pl"] == person.summary_pl

    for statement_name in (
        "BACKFILL_LEGACY_PUBLISHED_REVISIONS_SQL",
        "SET_BACKFILLED_POINTERS_SQL",
    ):
        await db_session.execute(text(_BACKFILL_MIGRATION[statement_name]))
    await db_session.commit()
    assert len(
        (
            await db_session.scalars(
                select(PublicationRevision).where(PublicationRevision.person_id == person.id)
            )
        ).all()
    ) == 1

    person.published_revision_id = None
    person.version += 1
    await db_session.flush()
    await db_session.execute(text(_BACKFILL_MIGRATION["SET_BACKFILLED_POINTERS_SQL"]))
    await db_session.refresh(person)
    assert person.published_revision_id is None


@pytest.mark.asyncio
async def test_publish_revision_rejects_changed_live_person(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )
    await PersonService(db_session).update_person(
        person,
        PersonUpdateSchema(summary_pl="Zmiana wykonana poza rewizją", expected_version=1),
        allow_published_update=True,
    )

    with pytest.raises(PersonVersionConflictError):
        await service.publish(
            revision.id,
            expected_version=2,
            author_id=None,
        )


@pytest.mark.asyncio
async def test_review_can_return_revision_to_draft_with_required_note(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    submitted = await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )

    returned = await service.return_to_draft(
        revision.id,
        expected_version=submitted.version,
        note="Uzupełnij źródło dla daty śmierci",
        author_id=None,
        audit_context=AuditContext(),
    )

    assert returned.status == PublicationRevisionStatus.DRAFT.value
    assert returned.version == 3
    assert returned.change_summary == "Uzupełnij źródło dla daty śmierci"
    assert person.summary_pl == "Aktualny opis publiczny"


@pytest.mark.asyncio
async def test_rejected_revision_is_retained_and_cannot_be_edited(
    db_session: AsyncSession,
) -> None:
    person = await _published_person(db_session)
    service = PublicationRevisionService(db_session)
    revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    submitted = await service.submit_for_review(
        revision.id,
        expected_version=revision.version,
        author_id=None,
    )

    rejected = await service.reject(
        revision.id,
        expected_version=submitted.version,
        note="Brak wystarczającego źródła biograficznego",
        author_id=None,
    )

    assert rejected.status == PublicationRevisionStatus.REJECTED.value
    assert rejected.version == 3
    with pytest.raises(PublicationRevisionStateError):
        await service.update_draft(
            revision.id,
            expected_version=rejected.version,
            changes={"summary_pl": "Nie powinno zostać zapisane"},
            author_id=None,
        )

    new_revision = await service.create_draft(
        person.id,
        expected_version=person.version,
        author_id=None,
    )
    assert new_revision.revision_number == 2
