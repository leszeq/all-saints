"""PostgreSQL integration coverage for editorial reports and workflow."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.editorial_service import (
    EditorialNotFoundError,
    EditorialPriority,
    EditorialService,
    EditorialTransitionError,
)
from src.domain.geography.models import Country, ReligiousOrder
from src.domain.hagiography.models import (
    Gender,
    Person,
    PersonType,
    PublicationStatus,
    StateOfLife,
)
from src.domain.identity.models import User, UserStatus
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
    SourceType,
)


async def _seed_editorial_data(db_session: AsyncSession) -> dict[str, object]:
    state = StateOfLife(
        id=uuid.uuid4(),
        name_pl="Kapłan",
        name_en="Priest",
    )
    country = Country(
        id=uuid.uuid4(),
        name_pl="Testlandia",
        name_en="Testland",
        iso_code_alpha2="XT",
        iso_code_alpha3="XTT",
    )
    order = ReligiousOrder(
        id=uuid.uuid4(),
        slug="zakon-redakcyjny",
        name="Zakon Redakcyjny",
    )
    editor = User(
        id=uuid.uuid4(),
        email="editorial@example.com",
        hashed_password="not-used-in-this-test",
        full_name="Redaktor Testowy",
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    incomplete = Person(
        id=uuid.uuid4(),
        slug="sw-jan-test-pierwszy",
        canonical_name="Św. Jan Test",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.REVIEW.value,
        gender=Gender.MALE.value,
        birth_year=1900,
        death_year=1980,
    )
    partial = Person(
        id=uuid.uuid4(),
        slug="jan-test-drugi",
        canonical_name="Jan Test",
        latin_name="Ioannes Test",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.DRAFT.value,
        gender=Gender.MALE.value,
        birth_year=1900,
        death_year=1980,
        state_of_life_id=state.id,
        summary_pl="Krótkie streszczenie",
    )
    ready = Person(
        id=uuid.uuid4(),
        slug="gotowy-do-publikacji",
        canonical_name="Gotowy do publikacji",
        person_type=PersonType.BLESSED.value,
        status=PublicationStatus.REVIEW.value,
        gender=Gender.UNKNOWN.value,
        birth_year=1910,
        death_year=1990,
        state_of_life_id=state.id,
        summary_pl="Zweryfikowane streszczenie",
        biography_pl="Zweryfikowany biogram",
    )
    archived = Person(
        id=uuid.uuid4(),
        slug="rekord-archiwalny",
        canonical_name="Rekord archiwalny",
        person_type=PersonType.CANDIDATE.value,
        status=PublicationStatus.ARCHIVED.value,
        gender=Gender.UNKNOWN.value,
    )
    website_without_url = Bibliography(
        id=uuid.uuid4(),
        source_type=SourceType.WEBSITE.value,
        title="Niepełne źródło internetowe",
    )
    historical_without_url = HistoricalSource(
        id=uuid.uuid4(),
        source_type=SourceType.MANUSCRIPT.value,
        title="Zdigitalizowany rękopis",
        is_digitized=True,
    )
    known_source = Bibliography(
        id=uuid.uuid4(),
        source_type=SourceType.BOOK.value,
        title="Zweryfikowana książka",
        reliability_score=5,
    )
    unknown_image = Image(
        id=uuid.uuid4(),
        person_id=incomplete.id,
        url="https://example.com/unknown.jpg",
        title="Obraz bez licencji",
        license=ImageLicense.UNKNOWN.value,
        is_primary=True,
    )
    verified_image = Image(
        id=uuid.uuid4(),
        person_id=ready.id,
        url="https://example.com/verified.jpg",
        source_url="https://example.com/source",
        title="Obraz zweryfikowany",
        license=ImageLicense.PUBLIC_DOMAIN.value,
        is_primary=True,
    )
    valid_link = PersonSource(
        id=uuid.uuid4(),
        person_id=ready.id,
        bibliography_id=known_source.id,
        is_primary=True,
    )
    orphan_link = PersonSource(
        id=uuid.uuid4(),
        person_id=partial.id,
        is_primary=False,
    )
    db_session.add_all(
        [
            state,
            country,
            order,
            editor,
            incomplete,
            partial,
            ready,
            archived,
            website_without_url,
            historical_without_url,
            known_source,
            unknown_image,
            verified_image,
            valid_link,
            orphan_link,
        ]
    )
    await db_session.commit()
    return {
        "incomplete": incomplete,
        "partial": partial,
        "ready": ready,
        "editor": editor,
    }


@pytest.mark.asyncio
async def test_editorial_queue_quality_report_and_dashboard_use_real_data(
    db_session: AsyncSession,
) -> None:
    seeded = await _seed_editorial_data(db_session)
    service = EditorialService(db_session)

    queue = await service.list_queue(page=1, per_page=10)
    assert queue.total == 3
    assert queue.counts.total == 3
    assert queue.counts.draft == 1
    assert queue.counts.review == 2
    assert queue.items[0].id == seeded["incomplete"].id
    assert queue.items[0].priority == EditorialPriority.URGENT
    assert queue.items[0].can_publish is False

    searched = await service.list_queue(
        search="Ioannes",
        status_filter=PublicationStatus.DRAFT,
        priority_filter=EditorialPriority.HIGH,
        attention_only=True,
    )
    assert [item.id for item in searched.items] == [seeded["partial"].id]
    assert (
        await service.list_queue(priority_filter=EditorialPriority.NORMAL, per_page=10)
    ).total == 1

    report = await service.quality_report()
    assert report.summary.records_with_issues == 2
    assert report.summary.duplicate_groups == 1
    assert report.summary.duplicate_records == 2
    assert report.summary.documented_persons == 1
    assert report.summary.undocumented_persons == 2
    assert report.summary.unknown_license_images == 1
    assert {group.confidence for group in report.duplicate_groups} == {95}
    item_types = {item.item_type for item in report.source_verification_items}
    assert {"bibliography", "historical_source", "image", "person_source"} <= item_types

    dashboard = await service.dashboard()
    assert dashboard.total_persons == 4
    assert dashboard.resources.users == 1
    assert dashboard.resources.countries == 1
    assert dashboard.resources.orders == 1
    assert dashboard.resources.bibliography == 2
    assert dashboard.unknown_license_images == 1
    assert len(dashboard.monthly_activity) == 12
    assert dashboard.queue_counts.total == 3
    assert dashboard.recent_records


@pytest.mark.asyncio
async def test_editorial_transition_validates_content_and_persists_version(
    db_session: AsyncSession,
) -> None:
    seeded = await _seed_editorial_data(db_session)
    service = EditorialService(db_session)
    incomplete = seeded["incomplete"]
    ready = seeded["ready"]
    editor = seeded["editor"]

    with pytest.raises(EditorialTransitionError, match="streszczenie, biogram, licencja"):
        await service.transition(
            incomplete.id,
            PublicationStatus.PUBLISHED,
            user_id=editor.id,
            granted_permissions={"persons:review"},
            expected_version=incomplete.version,
        )

    result = await service.transition(
        ready.id,
        PublicationStatus.PUBLISHED,
        user_id=editor.id,
        note="Zatwierdzone w teście integracyjnym",
        granted_permissions={"persons:review"},
        expected_version=ready.version,
    )
    assert result.previous_status == PublicationStatus.REVIEW.value
    assert result.status == PublicationStatus.PUBLISHED.value

    with pytest.raises(EditorialNotFoundError):
        await service.transition(
            uuid.uuid4(),
            PublicationStatus.REVIEW,
            user_id=editor.id,
            granted_permissions={"persons:submit"},
        )
