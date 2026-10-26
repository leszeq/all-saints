"""Privacy-preserving product analytics ingestion endpoint."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4, BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.domain.analytics.models import (
    ProductEvent,
    ProductEventDailyAggregate,
    ProductEventName,
    ProductFeedback,
    ProductFilterName,
    ProductQueryClass,
    ProductRelationKind,
    ProductSourceKind,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission

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


class ProductEventAggregateSchema(BaseModel):
    """One daily aggregate row with no raw session identifier."""

    model_config = ConfigDict(from_attributes=True)

    day: date
    event_name: ProductEventName
    query_class: ProductQueryClass | None = None
    event_count: int
    unique_sessions: int
    result_count_sum: int
    zero_results_count: int
    search_success_count: int
    generated_at: datetime


class ProductEventAggregatesResponseSchema(BaseModel):
    """Bounded aggregate response used by the PM dashboard."""

    start_date: date
    end_date: date
    generated_at: datetime
    items: list[ProductEventAggregateSchema]


@dataclass
class _AggregateBucket:
    day: date
    event_name: str
    query_class: str | None
    event_count: int = 0
    sessions: set[str] = field(default_factory=set)
    result_count_sum: int = 0
    zero_results_count: int = 0
    search_success_count: int = 0


def _resolve_date_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    resolved_end = end_date or datetime.now(UTC).date()
    resolved_start = start_date or (resolved_end - timedelta(days=27))
    if resolved_start > resolved_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date musi być wcześniejsza niż end_date")
    if (resolved_end - resolved_start).days > 30:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zakres agregacji nie może przekraczać 31 dni")
    return resolved_start, resolved_end


def _aggregate_events(events: Sequence[ProductEvent]) -> list[_AggregateBucket]:
    buckets: dict[tuple[date, str, str | None], _AggregateBucket] = {}
    for event in events:
        created_at = event.created_at
        event_day = created_at.astimezone(UTC).date() if created_at.tzinfo else created_at.date()
        key = (event_day, event.event_name, event.query_class)
        bucket = buckets.setdefault(
            key,
            _AggregateBucket(
                day=event_day,
                event_name=event.event_name,
                query_class=event.query_class,
            ),
        )
        bucket.event_count += 1
        bucket.sessions.add(event.session_id_hash)
        if event.event_name != ProductEventName.SEARCH_RESULTS.value or not event.properties:
            continue
        raw_result_count = event.properties.get("result_count")
        if not isinstance(raw_result_count, int) or isinstance(raw_result_count, bool):
            continue
        bucket.result_count_sum += raw_result_count
        if raw_result_count == 0:
            bucket.zero_results_count += 1
        elif raw_result_count > 0:
            bucket.search_success_count += 1
    return sorted(buckets.values(), key=lambda item: (item.day, item.event_name, item.query_class or ""))


def _bucket_schema(bucket: _AggregateBucket, generated_at: datetime) -> ProductEventAggregateSchema:
    return ProductEventAggregateSchema(
        day=bucket.day,
        event_name=bucket.event_name,
        query_class=bucket.query_class,
        event_count=bucket.event_count,
        unique_sessions=len(bucket.sessions),
        result_count_sum=bucket.result_count_sum,
        zero_results_count=bucket.zero_results_count,
        search_success_count=bucket.search_success_count,
        generated_at=generated_at,
    )


def _aggregate_response(
    start_date: date,
    end_date: date,
    items: list[ProductEventAggregateSchema],
) -> ProductEventAggregatesResponseSchema:
    return ProductEventAggregatesResponseSchema(
        start_date=start_date,
        end_date=end_date,
        generated_at=max((item.generated_at for item in items), default=datetime.now(UTC)),
        items=items,
    )


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


@router.post(
    "/aggregates/rebuild",
    response_model=ProductEventAggregatesResponseSchema,
    summary="Rebuild bounded product analytics aggregates",
    description="Rebuilds daily rows for a maximum 31-day range; only aggregate rows are returned.",
)
async def rebuild_product_event_aggregates(
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> ProductEventAggregatesResponseSchema:
    """Materialize daily aggregates for the protected PM dashboard."""
    resolved_start, resolved_end = _resolve_date_range(start_date, end_date)
    lower_bound = datetime.combine(resolved_start, time.min, tzinfo=UTC)
    upper_bound = datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=UTC)
    events = list(
        (
            await db.scalars(
                select(ProductEvent)
                .where(ProductEvent.created_at >= lower_bound, ProductEvent.created_at < upper_bound)
                .order_by(ProductEvent.created_at.asc())
            )
        ).all()
    )
    buckets = _aggregate_events(events)
    await db.execute(
        delete(ProductEventDailyAggregate).where(
            ProductEventDailyAggregate.day >= resolved_start,
            ProductEventDailyAggregate.day <= resolved_end,
        )
    )
    generated_at = datetime.now(UTC)
    db.add_all(
        [
            ProductEventDailyAggregate(
                day=bucket.day,
                event_name=bucket.event_name,
                query_class=bucket.query_class,
                event_count=bucket.event_count,
                unique_sessions=len(bucket.sessions),
                result_count_sum=bucket.result_count_sum,
                zero_results_count=bucket.zero_results_count,
                search_success_count=bucket.search_success_count,
                generated_at=generated_at,
            )
            for bucket in buckets
        ]
    )
    return _aggregate_response(
        resolved_start,
        resolved_end,
        [_bucket_schema(bucket, generated_at) for bucket in buckets],
    )


@router.get(
    "/aggregates",
    response_model=ProductEventAggregatesResponseSchema,
    summary="Read daily product analytics aggregates",
)
async def list_product_event_aggregates(
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "read")),
) -> ProductEventAggregatesResponseSchema:
    """Read aggregate rows without exposing raw event or session data."""
    resolved_start, resolved_end = _resolve_date_range(start_date, end_date)
    rows = list(
        (
            await db.scalars(
                select(ProductEventDailyAggregate)
                .where(
                    ProductEventDailyAggregate.day >= resolved_start,
                    ProductEventDailyAggregate.day <= resolved_end,
                )
                .order_by(
                    ProductEventDailyAggregate.day,
                    ProductEventDailyAggregate.event_name,
                    ProductEventDailyAggregate.query_class,
                )
            )
        ).all()
    )
    items = [ProductEventAggregateSchema.model_validate(row) for row in rows]
    return _aggregate_response(resolved_start, resolved_end, items)


__all__ = [
    "ProductEventAcceptedSchema",
    "ProductEventAggregateSchema",
    "ProductEventAggregatesResponseSchema",
    "ProductEventCreateSchema",
    "ProductEventPropertiesSchema",
    "hash_session_id",
    "record_product_event",
    "rebuild_product_event_aggregates",
    "list_product_event_aggregates",
    "router",
]
