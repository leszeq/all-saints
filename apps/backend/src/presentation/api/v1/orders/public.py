"""Public catalogue and details for religious communities."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.order_query_service import OrderQueryService
from src.application.services.order_service import OrderNotFoundError
from src.domain.geography.models import OrderCharism, ReligiousCommunityType
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.orders.responses import order_response
from src.presentation.api.v1.orders.schemas import (
    ReligiousOrderDetailSchema,
    ReligiousOrderMembershipSchema,
    ReligiousOrderSchema,
)

router = APIRouter()


async def list_orders(
    search: str | None = Query(None, max_length=100),
    charism: OrderCharism | None = None,
    spiritual_family: str | None = Query(None, max_length=80),
    community_type: ReligiousCommunityType | None = None,
    featured: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[ReligiousOrderSchema]:
    """Browse orders and congregations with public member counts."""
    rows = await OrderQueryService(db).list_orders(
        search=search,
        charism=charism.value if charism else None,
        spiritual_family=spiritual_family,
        community_type=community_type.value if community_type else None,
        featured=featured,
    )
    return [order_response(order, member_count) for order, member_count in rows]


@router.get(
    "/{id_or_slug}",
    response_model=ReligiousOrderDetailSchema,
    summary="Get religious community detail",
)
async def get_order(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db_session),
) -> ReligiousOrderDetailSchema:
    """Return history, mission, provenance, and linked catalogue people."""
    try:
        order, memberships = await OrderQueryService(db).get_order(id_or_slug)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    base = order_response(order, len(memberships))
    return ReligiousOrderDetailSchema(
        **base.model_dump(),
        members=[
            ReligiousOrderMembershipSchema.model_validate(membership) for membership in memberships
        ],
    )
