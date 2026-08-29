"""PostgreSQL integration coverage for religious-order editorial workflows."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.order_service import (
    OrderConflictError,
    OrderNotFoundError,
    OrderService,
)
from src.domain.geography.models import OrderCharism, ReligiousCommunityType
from src.domain.hagiography.models import Gender, Person, PersonType, PublicationStatus
from src.presentation.api.v1.orders.schemas import (
    OrderMembershipType,
    ReligiousOrderCreateSchema,
    ReligiousOrderMembershipCreateSchema,
    ReligiousOrderUpdateSchema,
)


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
async def test_order_crud_filters_and_slug_conflicts(db_session: AsyncSession) -> None:
    service = OrderService(db_session)
    franciscans = await service.create_order(
        ReligiousOrderCreateSchema(
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
        ReligiousOrderCreateSchema(
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
            ReligiousOrderCreateSchema(slug=franciscans.slug, name="Duplikat")
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
        ReligiousOrderUpdateSchema(
            slug="franciszkanie-zmienieni",
            name="Franciszkanie Zmienieni",
        ),
    )
    assert changed.slug == "franciszkanie-zmienieni"
    with pytest.raises(OrderConflictError):
        await service.update_order(
            changed.slug,
            ReligiousOrderUpdateSchema(slug=benedictines.slug),
        )

    await service.soft_delete_order(benedictines.slug)
    with pytest.raises(OrderNotFoundError):
        await service.get_order(benedictines.slug)


@pytest.mark.asyncio
async def test_order_memberships_hide_drafts_and_reject_duplicates(
    db_session: AsyncSession,
) -> None:
    service = OrderService(db_session)
    order = await service.create_order(
        ReligiousOrderCreateSchema(slug="wspolnota-test", name="Wspólnota Testowa")
    )
    published = await _person(db_session, "sw-opublikowany", PublicationStatus.PUBLISHED)
    draft = await _person(db_session, "szkic-czlonka", PublicationStatus.DRAFT)

    published_membership = await service.add_membership(
        order.slug,
        ReligiousOrderMembershipCreateSchema(
            person_id=published.id,
            is_founder=True,
            membership_type=OrderMembershipType.FOUNDER,
            entry_date="1920",
        ),
    )
    await service.add_membership(
        order.slug,
        ReligiousOrderMembershipCreateSchema(
            person_id=draft.id,
            membership_type=OrderMembershipType.MEMBER,
        ),
    )

    rows = await service.list_orders()
    assert rows[0][1] == 1
    _, public_members = await service.get_order(order.slug)
    assert [membership.person_id for membership in public_members] == [published.id]
    _, all_members = await service.get_order(order.slug, public_members_only=False)
    assert {membership.person_id for membership in all_members} == {published.id, draft.id}
    assert published_membership.person.canonical_name == published.canonical_name

    with pytest.raises(OrderConflictError):
        await service.add_membership(
            order.slug,
            ReligiousOrderMembershipCreateSchema(person_id=published.id),
        )
    with pytest.raises(OrderNotFoundError, match="Osoba"):
        await service.add_membership(
            order.slug,
            ReligiousOrderMembershipCreateSchema(person_id=uuid.uuid4()),
        )

    await service.delete_membership(order.slug, published.id)
    with pytest.raises(OrderNotFoundError, match="Powiązanie"):
        await service.delete_membership(order.slug, published.id)
    with pytest.raises(OrderNotFoundError, match="Wspólnota"):
        await service.get_order("nieistniejaca-wspolnota")
