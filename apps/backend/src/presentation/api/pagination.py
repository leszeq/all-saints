"""Shared, backwards-compatible pagination for list endpoints.

List bodies intentionally remain JSON arrays. Pagination metadata is exposed in
response headers so existing catalogue clients keep working while new clients can
navigate every page explicitly.
"""

from __future__ import annotations

from typing import Annotated, Any, TypeVar

from fastapi import Query, Response
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

PageNumber = Annotated[int, Query(ge=1, description="Numer strony, liczony od 1")]
PageSize = Annotated[
    int,
    Query(ge=1, le=500, description="Liczba rekordów na stronie (maks. 500)"),
]

PAGINATION_RESPONSE_DOCS: dict[int | str, dict[str, Any]] = {
    200: {
        "headers": {
            "X-Total-Count": {
                "description": "Łączna liczba rekordów pasujących do filtrów",
                "schema": {"type": "integer"},
            },
            "X-Page": {
                "description": "Bieżący numer strony",
                "schema": {"type": "integer"},
            },
            "X-Per-Page": {
                "description": "Rozmiar strony",
                "schema": {"type": "integer"},
            },
            "X-Total-Pages": {
                "description": "Łączna liczba stron",
                "schema": {"type": "integer"},
            },
        }
    }
}


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


def add_pagination_headers(
    response: Response,
    *,
    total: int,
    page: int,
    per_page: int,
) -> None:
    """Expose page metadata without changing the established array response body."""
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Per-Page"] = str(per_page)
    response.headers["X-Total-Pages"] = str((total + per_page - 1) // per_page)
