"""Validate and atomically import versioned religious-community documents."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.order_import_models import (
    PortableReligiousOrder,
    ReligiousOrderImportDocument,
    ReligiousOrderImportValidationResult,
)
from src.application.services.audit_service import AuditContext, add_audit_log
from src.application.services.order_service import OrderService
from src.domain.geography.models import Place, ReligiousOrder
from src.domain.hagiography.models import Person
from src.domain.identity.models import AuditAction


class ReligiousOrderImportError(ValueError):
    """Raised when an order document cannot be imported safely."""

    def __init__(self, validation: ReligiousOrderImportValidationResult) -> None:
        self.validation = validation
        super().__init__("Wspólnoty nie przeszły walidacji importu")


class ReligiousOrderImportService:
    """Validate and import community batches inside a caller-owned transaction."""

    _OPTIONAL_TEXT_FIELDS = (
        "name_la",
        "name_local",
        "abbreviation",
        "spiritual_family",
        "founder_name",
        "description",
        "description_en",
        "history",
        "mission",
        "motto",
        "source_title",
    )

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_import(
        self,
        document: ReligiousOrderImportDocument,
    ) -> ReligiousOrderImportValidationResult:
        """Normalize content and check duplicates and database references."""
        normalized = document.model_copy(deep=True)
        self._normalize_text(normalized.orders)
        errors: list[str] = []
        warnings: list[str] = []

        slugs = [order.slug for order in normalized.orders]
        names = [order.name.lower() for order in normalized.orders]
        self._append_repeated_values(
            values=slugs,
            label="slug",
            errors=errors,
        )
        self._append_repeated_values(
            values=names,
            label="nazwa wspólnoty",
            errors=errors,
        )

        existing_slugs = set(
            (
                await self.db.execute(
                    select(ReligiousOrder.slug).where(ReligiousOrder.slug.in_(set(slugs)))
                )
            ).scalars()
        )
        for slug in sorted(existing_slugs):
            errors.append(f"Slug „{slug}” jest już używany w tej bazie.")

        existing_names = set(
            (
                await self.db.execute(
                    select(func.lower(ReligiousOrder.name)).where(
                        func.lower(ReligiousOrder.name).in_(set(names)),
                        ReligiousOrder.deleted_at.is_(None),
                    )
                )
            ).scalars()
        )
        for order in normalized.orders:
            if order.name.lower() in existing_names:
                errors.append(f"Aktywna wspólnota o nazwie „{order.name}” już istnieje.")

        await self._validate_references(normalized.orders, errors)
        for order in normalized.orders:
            self._validate_order_content(order, errors, warnings)

        return ReligiousOrderImportValidationResult(
            can_import=not errors,
            errors=errors,
            warnings=warnings,
            normalized_document=normalized,
        )

    async def import_orders(
        self,
        document: ReligiousOrderImportDocument,
        *,
        audit_context: AuditContext,
    ) -> list[ReligiousOrder]:
        """Persist an entire validated batch or fail the caller's transaction."""
        validation = await self.validate_import(document)
        if not validation.can_import:
            raise ReligiousOrderImportError(validation)

        imported: list[ReligiousOrder] = []
        order_service = OrderService(self.db)
        for item in validation.normalized_document.orders:
            order = await order_service.create_order(item)
            imported.append(order)
            add_audit_log(
                self.db,
                context=audit_context,
                action=AuditAction.IMPORT,
                resource_type="orders",
                resource_id=order.id,
                new_value={
                    "id": str(order.id),
                    **item.model_dump(mode="json"),
                },
                extra_metadata={
                    "operation": "orders_json_import",
                    "schema_version": validation.normalized_document.schema_version,
                },
            )
        await self.db.flush()
        return imported

    def _normalize_text(self, orders: Iterable[PortableReligiousOrder]) -> None:
        for order in orders:
            order.name = order.name.strip()
            for field in self._OPTIONAL_TEXT_FIELDS:
                value = getattr(order, field)
                if isinstance(value, str):
                    setattr(order, field, value.strip() or None)

    def _append_repeated_values(
        self,
        *,
        values: list[str],
        label: str,
        errors: list[str],
    ) -> None:
        for value, count in sorted(Counter(values).items()):
            if count > 1:
                errors.append(f"Plik zawiera powtórzoną wartość {label}: „{value}”.")

    async def _validate_references(
        self,
        orders: list[PortableReligiousOrder],
        errors: list[str],
    ) -> None:
        place_ids = {order.founded_place_id for order in orders if order.founded_place_id}
        if place_ids:
            existing_places = set(
                (
                    await self.db.execute(
                        select(Place.id).where(
                            Place.id.in_(place_ids),
                            Place.deleted_at.is_(None),
                        )
                    )
                ).scalars()
            )
            for identifier in sorted(place_ids - existing_places, key=str):
                errors.append(f"Miejsce założenia {identifier} nie istnieje w tej bazie.")

        founder_ids = {order.founder_id for order in orders if order.founder_id}
        if founder_ids:
            existing_founders = set(
                (
                    await self.db.execute(
                        select(Person.id).where(
                            Person.id.in_(founder_ids),
                            Person.deleted_at.is_(None),
                        )
                    )
                ).scalars()
            )
            for identifier in sorted(founder_ids - existing_founders, key=str):
                errors.append(f"Założyciel {identifier} nie istnieje w tej bazie.")

    def _validate_order_content(
        self,
        order: PortableReligiousOrder,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        if len(order.name) < 2:
            errors.append(f"Wspólnota o slugu „{order.slug}” nie ma poprawnej nazwy.")
        if (
            order.founded_year is not None
            and order.suppressed_year is not None
            and order.suppressed_year < order.founded_year
        ):
            errors.append(f"{order.name}: rok zniesienia nie może poprzedzać roku założenia.")
        if (
            order.founded_year is not None
            and order.papal_approval_year is not None
            and order.papal_approval_year < order.founded_year
        ):
            errors.append(
                f"{order.name}: rok zatwierdzenia papieskiego nie może poprzedzać roku założenia."
            )
        if not any((order.description, order.history, order.mission)):
            warnings.append(f"{order.name}: brak opisu, historii i misji.")
        if not order.source_url and not order.source_title:
            warnings.append(f"{order.name}: brak informacji o źródle.")
        if order.is_suppressed and order.suppressed_year is None:
            warnings.append(f"{order.name}: wspólnota zniesiona nie ma podanego roku zniesienia.")
