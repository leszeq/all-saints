"""Protected validation and import of religious-community JSON documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.order_import_models import (
    ReligiousOrderImportDocument,
    ReligiousOrderImportValidationResult,
)
from src.application.services.order_import_service import (
    ReligiousOrderImportError,
    ReligiousOrderImportService,
)
from src.application.services.order_service import OrderConflictError
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.orders.responses import order_response
from src.presentation.api.v1.orders.schemas import ReligiousOrderSchema
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.post(
    "/import/validate",
    response_model=ReligiousOrderImportValidationResult,
    summary="Validate a religious-community JSON document",
)
async def validate_order_import(
    document: ReligiousOrderImportDocument,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("orders", "create")),
) -> ReligiousOrderImportValidationResult:
    """Check the complete batch without writing any community records."""
    return await ReligiousOrderImportService(db).validate_import(document)


@router.post(
    "/import",
    response_model=list[ReligiousOrderSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Import religious communities from a validated JSON document",
)
async def import_orders(
    document: ReligiousOrderImportDocument,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("orders", "create")),
) -> list[ReligiousOrderSchema]:
    """Create the complete batch atomically and audit each imported record."""
    service = ReligiousOrderImportService(db)
    try:
        imported = await service.import_orders(
            document,
            audit_context=audit_context_from_request(request, current_user),
        )
    except ReligiousOrderImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "errors": exc.validation.errors,
                "warnings": exc.validation.warnings,
            },
        ) from exc
    except OrderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return [order_response(order) for order in imported]
