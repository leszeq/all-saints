"""Read model for religious orders, congregations, and their members."""

from __future__ import annotations

import uuid
from typing import NamedTuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography.models import Person, PersonOrder, PublicationStatus


class OrderNotFoundError(ValueError):
    """Raised when an active religious community cannot be found."""


class OrderMembersPage(NamedTuple):
    """Typed result for a bounded public member listing."""

    order: ReligiousOrder
    memberships: list[PersonOrder]
    total: int
    page: int
    per_page: int


class OrderQueryService:
    """Query communities without exposing editorial mutation operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_orders(
        self,
        *,
        search: str | None = None,
        charism: str | None = None,
        spiritual_family: str | None = None,
        community_type: str | None = None,
        featured: bool | None = None,
        include_suppressed: bool = False,
        public_members_only: bool = True,
    ) -> list[tuple[ReligiousOrder, int]]:
        """Return communities with a context-appropriate member count."""
        member_person = and_(
            Person.id == PersonOrder.person_id,
            Person.deleted_at.is_(None),
        )
        if public_members_only:
            member_person = and_(
                member_person,
                Person.status == PublicationStatus.PUBLISHED.value,
            )
        query = (
            select(ReligiousOrder, func.count(func.distinct(Person.id)).label("member_count"))
            .outerjoin(PersonOrder, PersonOrder.order_id == ReligiousOrder.id)
            .outerjoin(Person, member_person)
            .where(ReligiousOrder.deleted_at.is_(None))
            .group_by(ReligiousOrder.id)
        )
        if not include_suppressed:
            query = query.where(ReligiousOrder.is_suppressed.is_(False))
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    ReligiousOrder.name.ilike(term),
                    ReligiousOrder.name_la.ilike(term),
                    ReligiousOrder.abbreviation.ilike(term),
                    ReligiousOrder.description.ilike(term),
                    ReligiousOrder.mission.ilike(term),
                )
            )
        if charism:
            query = query.where(ReligiousOrder.charism == charism)
        if spiritual_family:
            query = query.where(ReligiousOrder.spiritual_family == spiritual_family)
        if community_type:
            query = query.where(ReligiousOrder.community_type == community_type)
        if featured is not None:
            query = query.where(ReligiousOrder.is_featured == featured)

        query = query.order_by(
            ReligiousOrder.sort_order.asc(),
            ReligiousOrder.founded_year.asc().nullslast(),
            ReligiousOrder.name.asc(),
        )
        result = await self.db.execute(query)
        return [(order, int(member_count)) for order, member_count in result.all()]

    async def get_order(
        self,
        identifier: str,
        *,
        public_members_only: bool = True,
        include_suppressed: bool = False,
    ) -> tuple[ReligiousOrder, list[PersonOrder]]:
        """Fetch one community and its linked people by UUID or slug."""
        query = select(ReligiousOrder).where(
            ReligiousOrder.deleted_at.is_(None),
        )
        if not include_suppressed:
            query = query.where(ReligiousOrder.is_suppressed.is_(False))
        try:
            query = query.where(ReligiousOrder.id == uuid.UUID(identifier))
        except ValueError:
            query = query.where(ReligiousOrder.slug == identifier)

        order = (await self.db.execute(query)).scalar_one_or_none()
        if order is None:
            raise OrderNotFoundError("Wspólnota nie istnieje")

        memberships_query = (
            select(PersonOrder)
            .join(PersonOrder.person)
            .where(
                PersonOrder.order_id == order.id,
                Person.deleted_at.is_(None),
            )
            .options(selectinload(PersonOrder.person).selectinload(Person.images))
            .order_by(
                PersonOrder.is_founder.desc(),
                Person.birth_year.asc().nullslast(),
                Person.canonical_name.asc(),
            )
        )
        if public_members_only:
            memberships_query = memberships_query.where(
                Person.status == PublicationStatus.PUBLISHED.value
            )
        memberships = list((await self.db.execute(memberships_query)).scalars().unique().all())
        return order, memberships

    async def get_order_members_page(
        self,
        identifier: str,
        *,
        page: int = 1,
        per_page: int = 24,
        public_members_only: bool = True,
        include_suppressed: bool = False,
    ) -> OrderMembersPage:
        """Fetch one bounded page of members and the matching total count."""
        if page < 1:
            raise ValueError("Numer strony musi być większy lub równy 1")
        if per_page < 1:
            raise ValueError("Rozmiar strony musi być większy lub równy 1")

        query = select(ReligiousOrder).where(
            ReligiousOrder.deleted_at.is_(None),
        )
        if not include_suppressed:
            query = query.where(ReligiousOrder.is_suppressed.is_(False))
        try:
            query = query.where(ReligiousOrder.id == uuid.UUID(identifier))
        except ValueError:
            query = query.where(ReligiousOrder.slug == identifier)

        order = (await self.db.execute(query)).scalar_one_or_none()
        if order is None:
            raise OrderNotFoundError("Wspólnota nie istnieje")

        membership_filters = [
            PersonOrder.order_id == order.id,
            Person.deleted_at.is_(None),
        ]
        if public_members_only:
            membership_filters.append(Person.status == PublicationStatus.PUBLISHED.value)

        total = int(
            await self.db.scalar(
                select(func.count())
                .select_from(PersonOrder)
                .join(PersonOrder.person)
                .where(*membership_filters)
            )
            or 0
        )
        pages = max(1, -(-total // per_page))
        page = min(page, pages)
        memberships_query = (
            select(PersonOrder)
            .join(PersonOrder.person)
            .where(*membership_filters)
            .options(selectinload(PersonOrder.person).selectinload(Person.images))
            .order_by(
                PersonOrder.is_founder.desc(),
                Person.birth_year.asc().nullslast(),
                Person.canonical_name.asc(),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        memberships = list((await self.db.execute(memberships_query)).scalars().unique().all())
        return OrderMembersPage(order, memberships, total, page, per_page)
