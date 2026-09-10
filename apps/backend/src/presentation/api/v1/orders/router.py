"""Religious orders API composition and backwards-compatible exports."""

from fastapi import APIRouter, status

from src.presentation.api.v1.orders.editorial import (
    add_order_member,
    create_order,
    delete_order,
    delete_order_member,
    list_orders_for_management,
    update_order,
)
from src.presentation.api.v1.orders.editorial import router as editorial_router
from src.presentation.api.v1.orders.public import get_order, list_orders
from src.presentation.api.v1.orders.public import router as public_router
from src.presentation.api.v1.orders.responses import order_response
from src.presentation.api.v1.orders.schemas import (
    ReligiousOrderCreateSchema,
    ReligiousOrderDetailSchema,
    ReligiousOrderMembershipCreateSchema,
    ReligiousOrderMembershipSchema,
    ReligiousOrderSchema,
    ReligiousOrderUpdateSchema,
)

router = APIRouter()

_order_response = order_response

__all__ = [
    "ReligiousOrderCreateSchema",
    "ReligiousOrderDetailSchema",
    "ReligiousOrderMembershipCreateSchema",
    "ReligiousOrderMembershipSchema",
    "ReligiousOrderSchema",
    "ReligiousOrderUpdateSchema",
    "add_order_member",
    "create_order",
    "delete_order",
    "delete_order_member",
    "get_order",
    "list_orders",
    "list_orders_for_management",
    "order_response",
    "update_order",
]

# Register static editorial paths before the public slug catch-all.
router.add_api_route(
    "",
    list_orders,
    methods=["GET"],
    response_model=list[ReligiousOrderSchema],
    summary="List religious communities",
)
router.add_api_route(
    "",
    create_order,
    methods=["POST"],
    response_model=ReligiousOrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create religious community",
)
router.include_router(editorial_router)
router.include_router(public_router)
