"""Protected management of religious communities and their members."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.order_query_service import OrderQueryService
from src.application.services.order_service import (
    OrderConflictError,
    OrderNotFoundError,
    OrderService,
)
from src.application.services.published_content_guard import PublishedContentChangeError
from src.domain.geography.models import OrderCharism, ReligiousCommunityType
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.orders.responses import order_response
from src.presentation.api.v1.orders.schemas import (
    ReligiousOrderCreateSchema,
    ReligiousOrderMembershipCreateSchema,
    ReligiousOrderMembershipSchema,
    ReligiousOrderSchema,
    ReligiousOrderUpdateSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.get(
    "/management",
    response_model=list[ReligiousOrderSchema],
    summary="List religious communities for administration",
)
async def list_orders_for_management(
    search: str | None = Query(None, max_length=100),
    charism: OrderCharism | None = None,
    spiritual_family: str | None = Query(None, max_length=80),
    community_type: ReligiousCommunityType | None = None,
    featured: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("orders", "read")),
) -> list[ReligiousOrderSchema]:
    """Return active and suppressed communities with all editorial members counted."""
    rows = await OrderQueryService(db).list_orders(
        search=search,
        charism=charism.value if charism else None,
        spiritual_family=spiritual_family,
        community_type=community_type.value if community_type else None,
        featured=featured,
        include_suppressed=True,
        public_members_only=False,
    )
    return [order_response(order, member_count) for order, member_count in rows]


async def create_order(
    data: ReligiousOrderCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("orders", "create")),
) -> ReligiousOrderSchema:
    try:
        order = await OrderService(db).create_order(data)
    except OrderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return order_response(order)


@router.patch(
    "/{id_or_slug}",
    response_model=ReligiousOrderSchema,
    summary="Update religious community",
)
async def update_order(
    id_or_slug: str,
    data: ReligiousOrderUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("orders", "update")),
) -> ReligiousOrderSchema:
    try:
        order = await OrderService(db).update_order(id_or_slug, data)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return order_response(order)


@router.delete(
    "/{id_or_slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete religious community",
)
async def delete_order(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("orders", "delete")),
) -> Response:
    try:
        await OrderService(db).soft_delete_order(id_or_slug)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{id_or_slug}/members",
    response_model=ReligiousOrderMembershipSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Link a person to a religious community",
)
async def add_order_member(
    id_or_slug: str,
    data: ReligiousOrderMembershipCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> ReligiousOrderMembershipSchema:
    try:
        membership = await OrderService(db).add_membership(
            id_or_slug,
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            allow_published_update=current_user.has_permission("persons", "publish"),
        )
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PublishedContentChangeError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ReligiousOrderMembershipSchema.model_validate(membership)


@router.delete(
    "/{id_or_slug}/members/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlink a person from a religious community",
)
async def delete_order_member(
    id_or_slug: str,
    person_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("persons", "update")),
) -> Response:
    try:
        await OrderService(db).delete_membership(
            id_or_slug,
            person_id,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            allow_published_update=current_user.has_permission("persons", "publish"),
        )
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PublishedContentChangeError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
