"""Measure the public religious-order catalogue read path."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import Select, event, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.application.services.order_query_service import OrderQueryService
from src.domain.geography import models as _geography_models  # noqa: F401
from src.domain.geography.models import ReligiousOrder
from src.domain.hagiography import embedding_model as _embedding_model  # noqa: F401
from src.domain.hagiography import models as _hagiography_models  # noqa: F401
from src.domain.identity import models as _identity_models  # noqa: F401
from src.domain.liturgy import models as _liturgy_models  # noqa: F401
from src.domain.sources import models as _source_models  # noqa: F401
from src.infrastructure.db.session import get_engine


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Return the nearest-rank percentile without a third-party dependency."""
    if not values:
        raise ValueError("At least one benchmark sample is required")
    ordered = sorted(values)
    rank = max(1, int((percentile / 100) * len(ordered) + 0.999999))
    return ordered[min(rank, len(ordered)) - 1]


def _catalogue_statement(
    service: OrderQueryService, *, page: int, per_page: int
) -> Select[tuple[ReligiousOrder, int]]:
    """Build the same unfiltered page statement as the public read service."""
    return (
        service._orders_query(  # noqa: SLF001 - benchmark must inspect the production query
            search=None,
            charism=None,
            spiritual_family=None,
            community_type=None,
            featured=None,
            include_suppressed=False,
            public_members_only=True,
        )
        .order_by(
            ReligiousOrder.sort_order.asc(),
            ReligiousOrder.founded_year.asc().nullslast(),
            ReligiousOrder.name.asc(),
            ReligiousOrder.id.asc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    )


async def run_benchmark(*, iterations: int, page: int, per_page: int) -> dict[str, Any]:
    """Run sequential reads and collect timings, SQL counts, and query plans."""
    if iterations < 1:
        raise ValueError("iterations must be greater than zero")
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be greater than zero")

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    durations_ms: list[float] = []
    statement_counts: list[int] = []
    current_statement_count = 0

    def count_statement(*_args: object, **_kwargs: object) -> None:
        nonlocal current_statement_count
        current_statement_count += 1

    event.listen(engine.sync_engine, "before_cursor_execute", count_statement)
    try:
        async with session_factory() as session:
            service = OrderQueryService(session)
            for _ in range(iterations):
                current_statement_count = 0
                started = time.perf_counter()
                await service.list_orders_page(page=page, per_page=per_page)
                durations_ms.append((time.perf_counter() - started) * 1000)
                statement_counts.append(current_statement_count)

            page_statement = _catalogue_statement(service, page=page, per_page=per_page)
            count_statement_query = select(func.count()).select_from(
                page_statement.order_by(None).subquery()
            )
            page_sql = str(
                page_statement.compile(
                    dialect=engine.sync_engine.dialect,
                    compile_kwargs={"literal_binds": True},
                )
            )
            count_sql = str(
                count_statement_query.compile(
                    dialect=engine.sync_engine.dialect,
                    compile_kwargs={"literal_binds": True},
                )
            )
            async with engine.connect() as connection:
                page_plan = (
                    await connection.execute(
                        text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {page_sql}")
                    )
                ).scalar_one()
                count_plan = (
                    await connection.execute(
                        text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {count_sql}")
                    )
                ).scalar_one()

            total = int(
                await session.scalar(
                    select(func.count()).select_from(ReligiousOrder).where(
                        ReligiousOrder.deleted_at.is_(None),
                        ReligiousOrder.is_suppressed.is_(False),
                    )
                )
                or 0
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count_statement)
        await engine.dispose()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "path": "GET /api/v1/orders",
        "dataset": {"active_public_orders": total},
        "parameters": {"iterations": iterations, "page": page, "per_page": per_page},
        "latency_ms": {
            "median": round(median(durations_ms), 3),
            "p50": round(_percentile(durations_ms, 50), 3),
            "p95": round(_percentile(durations_ms, 95), 3),
            "p99": round(_percentile(durations_ms, 99), 3),
            "min": round(min(durations_ms), 3),
            "max": round(max(durations_ms), 3),
        },
        "sql_statements_per_read": {
            "samples": statement_counts,
            "min": min(statement_counts),
            "max": max(statement_counts),
            "stable": len(set(statement_counts)) == 1,
        },
        "explain": {"page": page_plan, "count": count_plan},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    return parser


async def _run(args: argparse.Namespace) -> None:
    payload = await run_benchmark(
        iterations=args.iterations,
        page=args.page,
        per_page=args.per_page,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the catalogue benchmark without mutating application data."""
    args = _build_parser().parse_args(argv)
    asyncio.run(_run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
