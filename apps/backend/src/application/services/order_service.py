"""Application service for religious orders, congregations, and memberships."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from src.application.commands.religious_orders import (
    AddReligiousOrderMembershipCommand,
    CreateReligiousOrderCommand,
    UpdateReligiousOrderCommand,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.order_query_service import (
    OrderNotFoundError,
    OrderQueryService,
)
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography.models import Person, PersonOrder
from src.domain.identity.models import AuditAction

__all__ = ["OrderConflictError", "OrderNotFoundError", "OrderService"]


class OrderConflictError(ValueError):
    """Raised when a slug or membership already exists."""


class OrderService(OrderQueryService):
    """Mutate communities with a legacy-compatible read interface."""

    async def _assert_slug_available(
        self, slug: str, *, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(ReligiousOrder.id).where(ReligiousOrder.slug == slug)
        if exclude_id is not None:
            query = query.where(ReligiousOrder.id != exclude_id)
        if (await self.db.execute(query)).scalar_one_or_none() is not None:
            raise OrderConflictError("Wspólnota o takim slugu już istnieje")

    async def create_order(self, data: CreateReligiousOrderCommand) -> ReligiousOrder:
        """Create a religious community record."""
        await self._assert_slug_available(data.slug)
        values = data.model_dump(mode="json")
        order = ReligiousOrder(**values)
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def update_order(
        self, identifier: str, data: UpdateReligiousOrderCommand
    ) -> ReligiousOrder:
        """Update editable community content."""
        order, _memberships = await self.get_order(
            identifier,
            public_members_only=False,
            include_suppressed=True,
        )
        changes = data.model_dump(exclude_unset=True, mode="json")
        if "slug" in changes and changes["slug"] != order.slug:
            await self._assert_slug_available(changes["slug"], exclude_id=order.id)
        for field, value in changes.items():
            setattr(order, field, value)
        order.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(order)
        return order

    async def soft_delete_order(self, identifier: str) -> None:
        """Soft-delete a community without deleting linked people."""
        order, _memberships = await self.get_order(
            identifier,
            public_members_only=False,
            include_suppressed=True,
        )
        membership_count = await self.db.scalar(
            select(func.count()).select_from(PersonOrder).where(PersonOrder.order_id == order.id)
        )
        if membership_count:
            raise OrderConflictError(
                "Nie można usunąć wspólnoty powiązanej z osobami. Najpierw usuń powiązania."
            )
        order.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def add_membership(
        self,
        identifier: str,
        data: AddReligiousOrderMembershipCommand,
        *,
        user_id: uuid.UUID | None = None,
        audit_context: AuditContext | None = None,
    ) -> PersonOrder:
        """Attach a person to a community with a documented membership role."""
        order, _memberships = await self.get_order(
            identifier,
            public_members_only=False,
            include_suppressed=True,
        )
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
        await self.db.flush()
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
        order, _memberships = await self.get_order(
            identifier,
            public_members_only=False,
            include_suppressed=True,
        )
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
        await self.db.flush()
