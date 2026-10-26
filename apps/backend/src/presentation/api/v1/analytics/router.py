"""Privacy-preserving product analytics ingestion endpoint."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4, BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.domain.analytics.models import (
    ProductEvent,
    ProductEventName,
    ProductFeedback,
    ProductFilterName,
    ProductQueryClass,
    ProductRelationKind,
    ProductSourceKind,
)
from src.infrastructure.db.session import get_db_session

router = APIRouter()


class ProductEventPropertiesSchema(BaseModel):
    """Small allowlist of aggregate dimensions accepted from the browser."""

    model_config = ConfigDict(extra="forbid")

    result_count: Annotated[int | None, Field(ge=0, le=10_000)] = None
    filter_name: ProductFilterName | None = None
    source_kind: ProductSourceKind | None = None
    relation_kind: ProductRelationKind | None = None
    feedback: ProductFeedback | None = None


class ProductEventCreateSchema(BaseModel):
    """Client event contract with no raw query, URL, title, or user identity."""

    model_config = ConfigDict(extra="forbid")

    event_name: ProductEventName
    session_id: UUID4
    query_class: ProductQueryClass | None = None
    properties: ProductEventPropertiesSchema = Field(default_factory=ProductEventPropertiesSchema)


class ProductEventAcceptedSchema(BaseModel):
    """Stable acknowledgement that does not expose database identifiers."""

    accepted: bool = True


def hash_session_id(session_id: uuid.UUID) -> str:
    """Turn an anonymous client UUID into a server-secret-bound digest."""
    return hmac.new(
        settings.APP_SECRET_KEY.encode("utf-8"),
        session_id.bytes,
        hashlib.sha256,
    ).hexdigest()


@router.post(
    "",
    response_model=ProductEventAcceptedSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Record an anonymous product event",
    description=(
        "Accept a bounded analytics event. Query text, URLs, titles, account identity, "
        "and arbitrary properties are intentionally rejected."
    ),
)
async def record_product_event(
    payload: ProductEventCreateSchema,
    db: AsyncSession = Depends(get_db_session),
) -> ProductEventAcceptedSchema:
    """Store a privacy-preserving event for later aggregate reporting."""
    db.add(
        ProductEvent(
            event_name=payload.event_name.value,
            query_class=payload.query_class.value if payload.query_class else None,
            session_id_hash=hash_session_id(payload.session_id),
            properties=payload.properties.model_dump(exclude_none=True),
        )
    )
    return ProductEventAcceptedSchema()


__all__ = [
    "ProductEventAcceptedSchema",
    "ProductEventCreateSchema",
    "ProductEventPropertiesSchema",
    "hash_session_id",
    "record_product_event",
    "router",
]
