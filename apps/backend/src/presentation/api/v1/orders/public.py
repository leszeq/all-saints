"""Public catalogue and details for religious communities."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.order_query_service import OrderQueryService
from src.application.services.order_service import OrderNotFoundError
from src.domain.geography.models import OrderCharism, ReligiousCommunityType
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PageNumber,
    PageSize,
    add_pagination_headers,
)
from src.presentation.api.v1.orders.responses import order_response
from src.presentation.api.v1.orders.schemas import (
    ReligiousOrderDetailSchema,
    ReligiousOrderMembershipSchema,
    ReligiousOrderSchema,
)

router = APIRouter()


async def list_orders(
    response: Response,
    search: str | None = Query(None, max_length=100),
    charism: OrderCharism | None = None,
    spiritual_family: str | None = Query(None, max_length=80),
    community_type: ReligiousCommunityType | None = None,
    featured: bool | None = None,
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[ReligiousOrderSchema]:
    """Browse orders and congregations with public member counts."""
    result = await OrderQueryService(db).list_orders_page(
        page=page,
        per_page=per_page,
        search=search,
        charism=charism.value if charism else None,
        spiritual_family=spiritual_family,
        community_type=community_type.value if community_type else None,
        featured=featured,
    )
    add_pagination_headers(response, total=result.total, page=result.page, per_page=result.per_page)
    return [order_response(order, member_count) for order, member_count in result.rows]


@router.get(
    "/{id_or_slug}",
    response_model=ReligiousOrderDetailSchema,
    summary="Get religious community detail",
)
async def get_order(
    id_or_slug: str,
    members_page: int = Query(1, ge=1, description="Numer strony członków"),
    members_per_page: int = Query(24, ge=1, le=100, description="Liczba członków na stronie"),
    db: AsyncSession = Depends(get_db_session),
) -> ReligiousOrderDetailSchema:
    """Return history, mission, provenance, and one bounded page of catalogue people."""
    try:
        page = await OrderQueryService(db).get_order_members_page(
            id_or_slug,
            page=members_page,
            per_page=members_per_page,
        )
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    pages = max(1, -(-page.total // page.per_page))
    base = order_response(page.order, page.total)
    return ReligiousOrderDetailSchema(
        **base.model_dump(),
        members=[
            ReligiousOrderMembershipSchema.model_validate(membership)
            for membership in page.memberships
        ],
        members_total=page.total,
        members_page=page.page,
        members_per_page=page.per_page,
        members_pages=pages,
    )
