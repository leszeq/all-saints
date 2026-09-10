"""Shared transport mapping for religious communities."""

from src.presentation.api.v1.orders.schemas import ReligiousOrderSchema


def order_response(order: object, member_count: int = 0) -> ReligiousOrderSchema:
    """Map an order model and its aggregate member count to the API schema."""
    response = ReligiousOrderSchema.model_validate(order)
    return response.model_copy(update={"member_count": member_count})
