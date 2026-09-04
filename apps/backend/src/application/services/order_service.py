"""Application service for religious orders, congregations, and memberships."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography.models import Person, PersonOrder, PublicationStatus
from src.domain.identity.models import AuditAction
from src.presentation.api.v1.orders.schemas import (
    ReligiousOrderCreateSchema,
    ReligiousOrderMembershipCreateSchema,
    ReligiousOrderUpdateSchema,
)


class OrderNotFoundError(ValueError):
    """Raised when an active religious community cannot be found."""


class OrderConflictError(ValueError):
    """Raised when a slug or membership already exists."""


class OrderService:
    """Read public community profiles and manage their editorial records."""

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
    ) -> list[tuple[ReligiousOrder, int]]:
        """Return active communities with the count of public catalogue people."""
        catalogue_person = and_(
            Person.id == PersonOrder.person_id,
            Person.deleted_at.is_(None),
            Person.status == PublicationStatus.PUBLISHED.value,
        )
        query = (
            select(ReligiousOrder, func.count(func.distinct(Person.id)).label("member_count"))
            .outerjoin(PersonOrder, PersonOrder.order_id == ReligiousOrder.id)
            .outerjoin(Person, catalogue_person)
            .where(
                ReligiousOrder.deleted_at.is_(None),
                ReligiousOrder.is_suppressed.is_(False),
            )
            .group_by(ReligiousOrder.id)
        )
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
        self, identifier: str, *, public_members_only: bool = True
    ) -> tuple[ReligiousOrder, list[PersonOrder]]:
        """Fetch one community and its linked people by UUID or slug."""
        query = select(ReligiousOrder).where(
            ReligiousOrder.deleted_at.is_(None),
            ReligiousOrder.is_suppressed.is_(False),
        )
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

    async def _assert_slug_available(
        self, slug: str, *, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(ReligiousOrder.id).where(ReligiousOrder.slug == slug)
        if exclude_id is not None:
            query = query.where(ReligiousOrder.id != exclude_id)
        if (await self.db.execute(query)).scalar_one_or_none() is not None:
            raise OrderConflictError("Wspólnota o takim slugu już istnieje")

    async def create_order(self, data: ReligiousOrderCreateSchema) -> ReligiousOrder:
        """Create a religious community record."""
        await self._assert_slug_available(data.slug)
        values = data.model_dump(mode="json")
        order = ReligiousOrder(**values)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def update_order(
        self, identifier: str, data: ReligiousOrderUpdateSchema
    ) -> ReligiousOrder:
        """Update editable community content."""
        order, _memberships = await self.get_order(identifier, public_members_only=False)
        changes = data.model_dump(exclude_unset=True, mode="json")
        if "slug" in changes and changes["slug"] != order.slug:
            await self._assert_slug_available(changes["slug"], exclude_id=order.id)
        for field, value in changes.items():
            setattr(order, field, value)
        order.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def soft_delete_order(self, identifier: str) -> None:
        """Soft-delete a community without deleting linked people."""
        order, _memberships = await self.get_order(identifier, public_members_only=False)
        order.deleted_at = datetime.now(UTC)
        await self.db.commit()

    async def add_membership(
        self,
        identifier: str,
        data: ReligiousOrderMembershipCreateSchema,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
    ) -> PersonOrder:
        """Attach a person to a community with a documented membership role."""
        order, _memberships = await self.get_order(identifier, public_members_only=False)
        person = await lock_person_for_snapshot(self.db, data.person_id)
        if person is None:
            raise OrderNotFoundError("Osoba nie istnieje")

        existing = await self.db.get(
            PersonOrder,
            {"person_id": person.id, "order_id": order.id},
        )
        if existing is not None:
            raise OrderConflictError("Osoba jest już przypisana do tej wspólnoty")

        previous_snapshot = await serialize_person_snapshot(self.db, person)
        membership = PersonOrder(
            person_id=person.id,
            order_id=order.id,
            **data.model_dump(exclude={"person_id"}, mode="json"),
        )
        self.db.add(membership)
        await self.db.flush()
        previous_snapshot, current_snapshot = await append_relation_version(
            self.db,
            person,
            previous_snapshot=previous_snapshot,
            changed_by_id=user_id,
            change_summary="Dodanie przynależności zakonnej",
        )
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(user_id),
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
            extra_metadata={"relation": "orders", "operation": "add"},
        )
        await self.db.commit()
        result = await self.db.execute(
            select(PersonOrder)
            .where(
                PersonOrder.person_id == person.id,
                PersonOrder.order_id == order.id,
            )
            .options(selectinload(PersonOrder.person).selectinload(Person.images))
        )
        return result.scalar_one()

    async def delete_membership(
        self,
        identifier: str,
        person_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
    ) -> None:
        """Remove one person-to-community link."""
        order, _memberships = await self.get_order(identifier, public_members_only=False)
        person = await lock_person_for_snapshot(self.db, person_id)
        if person is None:
            raise OrderNotFoundError("Osoba nie istnieje")
        membership = await self.db.get(
            PersonOrder,
            {"person_id": person_id, "order_id": order.id},
        )
        if membership is None:
            raise OrderNotFoundError("Powiązanie nie istnieje")
        previous_snapshot = await serialize_person_snapshot(self.db, person)
        await self.db.delete(membership)
        await self.db.flush()
        previous_snapshot, current_snapshot = await append_relation_version(
            self.db,
            person,
            previous_snapshot=previous_snapshot,
            changed_by_id=user_id,
            change_summary="Usunięcie przynależności zakonnej",
        )
        add_audit_log(
            self.db,
            context=audit_context or AuditContext.for_user(user_id),
            action=AuditAction.UPDATE,
            resource_type="persons",
            resource_id=person.id,
            old_value=previous_snapshot,
            new_value=current_snapshot,
            extra_metadata={"relation": "orders", "operation": "remove"},
        )
        await self.db.commit()
