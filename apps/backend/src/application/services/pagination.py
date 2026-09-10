"""Shared execution helper for paginated application queries."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


async def execute_page(
    db: AsyncSession,
    statement: Select[tuple[T]],
    *,
    page: int,
    per_page: int,
) -> tuple[list[T], int]:
    """Execute one deterministic page and its matching count query."""
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int((await db.execute(count_statement)).scalar_one())
    result = await db.execute(statement.offset((page - 1) * per_page).limit(per_page))
    return list(result.scalars().all()), total
