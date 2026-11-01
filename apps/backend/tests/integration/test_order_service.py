"""PostgreSQL integration coverage for religious-order editorial workflows."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.commands.religious_orders import (
    AddReligiousOrderMembershipCommand,
    CreateReligiousOrderCommand,
    UpdateReligiousOrderCommand,
)
from src.application.services.order_query_service import OrderQueryService
from src.application.services.order_service import (
    OrderConflictError,
    OrderNotFoundError,
    OrderService,
)
from src.application.services.published_content_guard import PublishedContentChangeError
from src.domain.geography.models import (
    OrderCharism,
    OrderMembershipType,
    ReligiousCommunityType,
    ReligiousOrder,
)
from src.domain.hagiography.models import (
    Gender,
    Person,
    PersonType,
    PersonVersion,
    PublicationStatus,
)
from src.domain.identity.models import AuditLog


async def _person(db_session: AsyncSession, slug: str, status: PublicationStatus) -> Person:
    person = Person(
        id=uuid.uuid4(),
        slug=slug,
        canonical_name=slug.replace("-", " ").title(),
        person_type=PersonType.SAINT.value,
        status=status.value,
        gender=Gender.UNKNOWN.value,
        birth_year=1900,
    )
    db_session.add(person)
    await db_session.commit()
    return person


@pytest.mark.asyncio
async def test_order_service_defers_commit_to_unit_of_work(
    db_session: AsyncSession,
    test_engine,
) -> None:
    order = await OrderService(db_session).create_order(
        CreateReligiousOrderCommand(
            slug="transakcja-zakonu-test",
            name="Transakcja Zakonu Test",
        )
    )
    observer_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with observer_factory() as observer:
        before_commit = await observer.scalar(
            select(ReligiousOrder).where(ReligiousOrder.id == order.id)
        )
        assert before_commit is None

        await db_session.commit()

        after_commit = await observer.scalar(
            select(ReligiousOrder).where(ReligiousOrder.id == order.id)
        )
        assert after_commit is not None


@pytest.mark.asyncio
async def test_order_crud_filters_and_slug_conflicts(db_session: AsyncSession) -> None:
    service = OrderService(db_session)
    franciscans = await service.create_order(
        CreateReligiousOrderCommand(
            slug="franciszkanie-test",
            name="Franciszkanie Testowi",
            abbreviation="OFT",
            community_type=ReligiousCommunityType.RELIGIOUS_ORDER,
            spiritual_family="franciscan",
            charism=OrderCharism.MENDICANT,
            founded_year=1209,
            description="Wspólnota testowa",
            mission="Głoszenie Ewangelii",
            is_featured=True,
            sort_order=1,
        )
    )
    benedictines = await service.create_order(
        CreateReligiousOrderCommand(
            slug="benedyktyni-test",
            name="Benedyktyni Testowi",
            community_type=ReligiousCommunityType.MONASTIC_FAMILY,
            spiritual_family="benedictine",
            charism=OrderCharism.MONASTIC,
            founded_year=529,
            sort_order=2,
        )
    )

    with pytest.raises(OrderConflictError):
        await service.create_order(
            CreateReligiousOrderCommand(slug=franciscans.slug, name="Duplikat")
        )

    assert [order.id for order, _ in await service.list_orders(search="Ewangelii")] == [
        franciscans.id
    ]
    assert [
        order.id
        for order, _ in await service.list_orders(
            charism=OrderCharism.MONASTIC.value,
            spiritual_family="benedictine",
            community_type=ReligiousCommunityType.MONASTIC_FAMILY.value,
            featured=False,
        )
    ] == [benedictines.id]

    changed = await service.update_order(
        str(franciscans.id),
        UpdateReligiousOrderCommand(
            slug="franciszkanie-zmienieni",
            name="Franciszkanie Zmienieni",
        ),
    )
    assert changed.slug == "franciszkanie-zmienieni"
    with pytest.raises(OrderConflictError):
        await service.update_order(
            changed.slug,
            UpdateReligiousOrderCommand(slug=benedictines.slug),
        )

    await service.update_order(
        benedictines.slug,
        UpdateReligiousOrderCommand(is_suppressed=True),
    )
    with pytest.raises(OrderNotFoundError):
        await service.get_order(benedictines.slug)
    management_rows = await service.list_orders(
        include_suppressed=True,
        public_members_only=False,
    )
    assert {order.id for order, _ in management_rows} == {franciscans.id, benedictines.id}

    restored_for_edit = await service.update_order(
        benedictines.slug,
        UpdateReligiousOrderCommand(is_suppressed=False),
    )
    assert restored_for_edit.is_suppressed is False
    await service.soft_delete_order(benedictines.slug)
    with pytest.raises(OrderNotFoundError):
        await service.get_order(benedictines.slug)


@pytest.mark.asyncio
async def test_order_memberships_hide_drafts_and_reject_duplicates(
    db_session: AsyncSession,
) -> None:
    service = OrderService(db_session)
    order = await service.create_order(
        CreateReligiousOrderCommand(slug="wspolnota-test", name="Wspólnota Testowa")
    )
    published = await _person(db_session, "sw-opublikowany", PublicationStatus.PUBLISHED)
    published_two = await _person(
        db_session,
        "sw-opublikowany-drugi",
        PublicationStatus.PUBLISHED,
    )
    draft = await _person(db_session, "szkic-czlonka", PublicationStatus.DRAFT)

    with pytest.raises(PublishedContentChangeError, match="persons:publish"):
        await service.add_membership(
            order.slug,
            AddReligiousOrderMembershipCommand(person_id=published.id),
        )

    published_membership = await service.add_membership(
        order.slug,
        AddReligiousOrderMembershipCommand(
            person_id=published.id,
            is_founder=True,
            membership_type=OrderMembershipType.FOUNDER,
            entry_date="1920",
        ),
        allow_published_update=True,
    )
    await service.add_membership(
        order.slug,
        AddReligiousOrderMembershipCommand(
            person_id=draft.id,
            membership_type=OrderMembershipType.MEMBER,
        ),
    )
    await service.add_membership(
        order.slug,
        AddReligiousOrderMembershipCommand(
            person_id=published_two.id,
            membership_type=OrderMembershipType.MEMBER,
        ),
        allow_published_update=True,
    )
    await db_session.refresh(published)
    membership_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == published.id,
                PersonVersion.version_number == 2,
            )
        )
    ).scalar_one()
    assert membership_version.snapshot["orders"][0]["order_id"] == str(order.id)

    rows = await service.list_orders()
    assert rows[0][1] == 2
    _, public_members = await service.get_order(order.slug)
    assert {membership.person_id for membership in public_members} == {
        published.id,
        published_two.id,
    }
    _, all_members = await service.get_order(order.slug, public_members_only=False)
    assert {membership.person_id for membership in all_members} == {
        published.id,
        published_two.id,
        draft.id,
    }
    page = await service.get_order_members_page(order.slug, page=2, per_page=1)
    assert page.total == 2
    assert len(page.memberships) == 1
    assert page.memberships[0].person_id in {published.id, published_two.id}
    assert published_membership.person.canonical_name == published.canonical_name

    with pytest.raises(OrderConflictError):
        await service.add_membership(
            order.slug,
            AddReligiousOrderMembershipCommand(person_id=published.id),
            allow_published_update=True,
        )
    with pytest.raises(OrderConflictError, match="powiązanej z osobami"):
        await service.soft_delete_order(order.slug)
    with pytest.raises(OrderNotFoundError, match="Osoba"):
        await service.add_membership(
            order.slug,
            AddReligiousOrderMembershipCommand(person_id=uuid.uuid4()),
        )

    await service.delete_membership(
        order.slug,
        published.id,
        allow_published_update=True,
    )
    await db_session.refresh(published)
    removal_version = (
        await db_session.execute(
            select(PersonVersion).where(
                PersonVersion.person_id == published.id,
                PersonVersion.version_number == 3,
            )
        )
    ).scalar_one()
    assert removal_version.snapshot["orders"] == []
    audit_events = list(
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == published.id)
                .order_by(AuditLog.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert [event.extra_metadata["operation"] for event in audit_events] == [
        "add",
        "remove",
    ]
    with pytest.raises(OrderNotFoundError, match="Powiązanie"):
        await service.delete_membership(
            order.slug,
            published.id,
            allow_published_update=True,
        )
    with pytest.raises(OrderNotFoundError, match="Wspólnota"):
        await service.get_order("nieistniejaca-wspolnota")


@pytest.mark.asyncio
async def test_order_catalogue_page_is_bounded_and_stably_sorted(
    db_session: AsyncSession,
) -> None:
    service = OrderService(db_session)
    first = await service.create_order(
        CreateReligiousOrderCommand(
            slug="katalog-paginacja-pierwszy",
            name="Katalog Paginacja Pierwszy",
            founded_year=1200,
        )
    )
    second = await service.create_order(
        CreateReligiousOrderCommand(
            slug="katalog-paginacja-drugi",
            name="Katalog Paginacja Drugi",
            founded_year=1300,
        )
    )

    result = await OrderQueryService(db_session).list_orders_page(
        search="Katalog Paginacja",
        page=2,
        per_page=1,
    )

    assert result.total == 2
    assert result.page == 2
    assert result.per_page == 1
    assert len(result.rows) == 1
    assert result.rows[0][0].id == second.id
    assert first.id != second.id
