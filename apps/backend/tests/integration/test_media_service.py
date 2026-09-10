"""Integration coverage for media catalogue application queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.media_service import MediaService
from src.domain.hagiography.models import Gender, Person, PersonType, PublicationStatus
from src.domain.sources.models import Document, Image, ImageLicense


async def test_media_catalogue_filters_orders_and_paginates_active_records(
    db_session: AsyncSession,
) -> None:
    first_person = Person(
        slug="sw-media-pierwszy",
        canonical_name="Św. Media Pierwszy",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
    )
    second_person = Person(
        slug="sw-media-drugi",
        canonical_name="Św. Media Drugi",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.UNKNOWN.value,
    )
    db_session.add_all([first_person, second_person])
    await db_session.flush()

    now = datetime.now(UTC)
    primary_image = Image(
        person_id=first_person.id,
        url="https://example.test/primary.jpg",
        license=ImageLicense.CC_BY.value,
        is_primary=True,
        sort_order=10,
    )
    secondary_image = Image(
        person_id=first_person.id,
        url="https://example.test/secondary.jpg",
        license=ImageLicense.CC_BY.value,
        is_primary=False,
        sort_order=1,
    )
    db_session.add_all(
        [
            primary_image,
            secondary_image,
            Image(
                person_id=second_person.id,
                url="https://example.test/other-person.jpg",
                license=ImageLicense.CC_BY.value,
            ),
            Image(
                person_id=first_person.id,
                url="https://example.test/deleted.jpg",
                license=ImageLicense.CC_BY.value,
                deleted_at=now,
            ),
        ]
    )

    newest_document = Document(
        person_id=first_person.id,
        title="Nowszy dokument",
        created_at=now,
    )
    older_document = Document(
        person_id=first_person.id,
        title="Starszy dokument",
        created_at=now - timedelta(days=1),
    )
    db_session.add_all(
        [
            newest_document,
            older_document,
            Document(
                person_id=second_person.id,
                title="Dokument innej osoby",
                created_at=now + timedelta(days=1),
            ),
            Document(
                person_id=first_person.id,
                title="Usunięty dokument",
                created_at=now + timedelta(days=2),
                deleted_at=now,
            ),
        ]
    )
    await db_session.flush()

    service = MediaService(db_session)
    first_image_page, image_total = await service.list_images(
        person_id=first_person.id,
        license=ImageLicense.CC_BY,
        page=1,
        per_page=1,
    )
    second_image_page, _ = await service.list_images(
        person_id=first_person.id,
        license=ImageLicense.CC_BY,
        page=2,
        per_page=1,
    )
    documents, document_total = await service.list_documents(
        person_id=first_person.id,
        page=1,
        per_page=10,
    )

    assert image_total == 2
    assert [item.id for item in first_image_page] == [primary_image.id]
    assert [item.id for item in second_image_page] == [secondary_image.id]
    assert document_total == 2
    assert [item.id for item in documents] == [newest_document.id, older_document.id]
