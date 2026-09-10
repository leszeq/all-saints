"""PostgreSQL coverage for religious-community JSON imports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.religious_orders import CreateReligiousOrderCommand
from src.application.order_import_models import ReligiousOrderImportDocument
from src.application.services.audit_service import AuditContext
from src.application.services.order_import_service import (
    ReligiousOrderImportError,
    ReligiousOrderImportService,
)
from src.application.services.order_service import OrderService
from src.core.security import jwt_service
from src.domain.geography.models import ReligiousOrder
from src.domain.identity.models import (
    AuditAction,
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)


async def _importer_headers(db_session: AsyncSession) -> dict[str, str]:
    role = Role(name="orders-importer-test", display_name="Importer wspólnot")
    permission = Permission(
        resource="orders",
        action="create",
        description="Importowanie wspólnot",
    )
    user = User(
        email="orders-importer@example.com",
        hashed_password="not-used-by-token-tests",
        full_name="Importer Wspólnot",
        status=UserStatus.ACTIVE,
        is_verified=True,
    )
    db_session.add_all([role, permission, user])
    await db_session.flush()
    db_session.add_all(
        [
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                granted_at=datetime.now(UTC),
            ),
            UserRole(
                user_id=user.id,
                role_id=role.id,
                assigned_at=datetime.now(UTC),
                assigned_by_id=None,
            ),
        ]
    )
    await db_session.commit()
    token = jwt_service.create_access_token(
        user_id=user.id,
        email=user.email,
        roles=[role.name],
    )
    return {"Authorization": f"Bearer {token}"}


async def test_order_import_validates_persists_and_audits_complete_batch(
    db_session: AsyncSession,
) -> None:
    document = ReligiousOrderImportDocument.model_validate(
        {
            "schema_version": 1,
            "orders": [
                {
                    "slug": "karmelici-bosi-import",
                    "name": "  Karmelici bosi  ",
                    "name_la": "  Ordo Fratrum Discalceatorum  ",
                    "abbreviation": "OCD",
                    "community_type": "religious_order",
                    "spiritual_family": "karmelitańska",
                    "founded_year": 1593,
                    "charism": "contemplative",
                    "description": "Reformowana gałąź rodziny karmelitańskiej.",
                    "history": "Wspólnota ukształtowana przez reformę Karmelu.",
                    "mission": "Modlitwa kontemplacyjna i apostolstwo duchowości.",
                    "source_title": "Oficjalna strona Zakonu Karmelitów Bosych",
                    "source_url": "https://www.carmelitaniscalzi.com/",
                },
                {
                    "slug": "wspolnota-minimalna-import",
                    "name": "Wspólnota minimalna",
                },
            ],
        }
    )
    service = ReligiousOrderImportService(db_session)

    validation = await service.validate_import(document)

    assert validation.can_import is True
    assert validation.errors == []
    assert len(validation.warnings) == 2
    assert validation.normalized_document.orders[0].name == "Karmelici bosi"
    assert validation.normalized_document.orders[0].name_la == ("Ordo Fratrum Discalceatorum")

    imported = await service.import_orders(
        validation.normalized_document,
        audit_context=AuditContext(user_email="importer@example.com"),
    )

    assert [order.slug for order in imported] == [
        "karmelici-bosi-import",
        "wspolnota-minimalna-import",
    ]
    assert await db_session.scalar(select(func.count()).select_from(ReligiousOrder)) == 2
    audit_logs = list(
        (
            await db_session.execute(
                select(AuditLog)
                .where(AuditLog.resource_type == "orders")
                .order_by(AuditLog.created_at.asc())
            )
        ).scalars()
    )
    assert len(audit_logs) == 2
    assert all(log.action == AuditAction.IMPORT.value for log in audit_logs)
    assert all(log.extra_metadata["operation"] == "orders_json_import" for log in audit_logs)


async def test_order_import_rejects_batch_before_any_record_is_created(
    db_session: AsyncSession,
) -> None:
    await OrderService(db_session).create_order(
        CreateReligiousOrderCommand(
            slug="zajety-slug-importu",
            name="Istniejąca wspólnota",
        )
    )
    document = ReligiousOrderImportDocument.model_validate(
        {
            "orders": [
                {
                    "slug": "nowa-wspolnota-import",
                    "name": "Nowa wspólnota",
                },
                {
                    "slug": "zajety-slug-importu",
                    "name": "Druga nowa wspólnota",
                    "founded_place_id": str(uuid.uuid4()),
                    "founder_id": str(uuid.uuid4()),
                    "founded_year": 1700,
                    "papal_approval_year": 1600,
                    "suppressed_year": 1500,
                },
            ]
        }
    )
    service = ReligiousOrderImportService(db_session)

    validation = await service.validate_import(document)

    assert validation.can_import is False
    assert any("zajety-slug-importu" in error for error in validation.errors)
    assert any("Miejsce założenia" in error for error in validation.errors)
    assert any("Założyciel" in error for error in validation.errors)
    assert any("rok zniesienia" in error for error in validation.errors)
    assert any("rok zatwierdzenia" in error for error in validation.errors)

    with pytest.raises(ReligiousOrderImportError):
        await service.import_orders(document, audit_context=AuditContext())

    active_slugs = set(
        (
            await db_session.execute(
                select(ReligiousOrder.slug).where(ReligiousOrder.deleted_at.is_(None))
            )
        ).scalars()
    )
    assert active_slugs == {"zajety-slug-importu"}


async def test_order_import_api_exposes_validation_and_atomic_creation(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers = await _importer_headers(db_session)
    payload = {
        "schema_version": 1,
        "orders": [
            {
                "slug": "norbertanie-api-import",
                "name": "Norbertanie — import API",
                "community_type": "religious_order",
                "charism": "monastic",
                "history": "Wspólnota kanoników regularnych założona w XII wieku.",
                "mission": "Liturgia, duszpasterstwo i życie wspólnotowe.",
                "source_title": "Źródło testowe",
            }
        ],
    }

    validation_response = await async_client.post(
        "/api/v1/orders/import/validate",
        headers=headers,
        json=payload,
    )
    import_response = await async_client.post(
        "/api/v1/orders/import",
        headers=headers,
        json=payload,
    )

    assert validation_response.status_code == 200
    assert validation_response.json()["can_import"] is True
    assert import_response.status_code == 201
    assert [item["slug"] for item in import_response.json()] == ["norbertanie-api-import"]
    persisted = await db_session.scalar(
        select(ReligiousOrder).where(ReligiousOrder.slug == "norbertanie-api-import")
    )
    assert persisted is not None
