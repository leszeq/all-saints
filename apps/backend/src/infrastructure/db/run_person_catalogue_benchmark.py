"""Measure the public person catalogue and search read paths."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any, cast

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.application.services.person_query_service import PersonQueryService
from src.domain.geography import models as _geography_models  # noqa: F401
from src.domain.hagiography import embedding_model as _embedding_model  # noqa: F401
from src.domain.hagiography import models as _hagiography_models  # noqa: F401
from src.domain.identity import models as _identity_models  # noqa: F401
from src.domain.liturgy import models as _liturgy_models  # noqa: F401
from src.domain.sources import models as _source_models  # noqa: F401
from src.infrastructure.db.session import get_engine

type DriverParameters = Mapping[str, object] | Sequence[object] | None


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Return the nearest-rank percentile without a third-party dependency."""
    if not values:
        raise ValueError("At least one benchmark sample is required")
    ordered = sorted(values)
    rank = max(1, int((percentile / 100) * len(ordered) + 0.999999))
    return ordered[min(rank, len(ordered)) - 1]


def _latency_summary(durations_ms: Sequence[float]) -> dict[str, float]:
    """Summarize a sequence of request durations in milliseconds."""
    return {
        "median": round(median(durations_ms), 3),
        "p50": round(_percentile(durations_ms, 50), 3),
        "p95": round(_percentile(durations_ms, 95), 3),
        "p99": round(_percentile(durations_ms, 99), 3),
        "min": round(min(durations_ms), 3),
        "max": round(max(durations_ms), 3),
    }


def _statement_kind(statement: str) -> str:
    """Classify SELECT statements used by the catalogue read path."""
    normalized = " ".join(statement.strip().split()).lower()
    if normalized.startswith("select count("):
        return "count"
    if " from persons " in normalized and " limit " in normalized:
        return "page"
    return "relation"


async def _explain(
    engine: AsyncEngine,
    statement: tuple[str, DriverParameters] | None,
) -> object | None:
    """Run PostgreSQL EXPLAIN for a captured parameterized statement."""
    if statement is None:
        return None
    sql, parameters = statement
    async with engine.connect() as connection:
        result = await connection.exec_driver_sql(
            f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}",
            parameters,
        )
        return cast(object, result.scalar_one())


async def _run_scenario(
    *,
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
    iterations: int,
    page: int,
    per_page: int,
    search: str | None,
) -> dict[str, Any]:
    """Run one public read scenario and retain plans from its final sample."""
    durations_ms: list[float] = []
    statement_counts: list[int] = []
    captured: list[tuple[str, DriverParameters]] = []
    last_sample: list[tuple[str, DriverParameters]] = []

    def capture_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        parameters: DriverParameters,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            captured.append((statement, parameters))

    event.listen(engine.sync_engine, "before_cursor_execute", capture_statement)
    try:
        async with session_factory() as session:
            service = PersonQueryService(session)
            total = 0
            for _ in range(iterations):
                captured.clear()
                started = time.perf_counter()
                _, total = await service.list_persons(
                    page=page,
                    per_page=per_page,
                    search=search,
                    published_only=True,
                    include_translations=True,
                )
                durations_ms.append((time.perf_counter() - started) * 1000)
                statement_counts.append(len(captured))
                last_sample = list(captured)

            page_statement = next(
                (item for item in last_sample if _statement_kind(item[0]) == "page"),
                None,
            )
            count_statement = next(
                (item for item in last_sample if _statement_kind(item[0]) == "count"),
                None,
            )
            page_plan, count_plan = await asyncio.gather(
                _explain(engine, page_statement),
                _explain(engine, count_statement),
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_statement)

    return {
        "search": search,
        "dataset_matches": total,
        "latency_ms": _latency_summary(durations_ms),
        "sql_statements_per_read": {
            "samples": statement_counts,
            "min": min(statement_counts),
            "max": max(statement_counts),
            "stable": len(set(statement_counts)) == 1,
        },
        "explain": {"page": page_plan, "count": count_plan},
    }


async def run_benchmark(
    *, iterations: int, page: int, per_page: int, search: str
) -> dict[str, Any]:
    """Run catalogue and search scenarios without mutating application data."""
    if iterations < 1:
        raise ValueError("iterations must be greater than zero")
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be greater than zero")

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        scenarios = {
            "catalogue": await _run_scenario(
                engine=engine,
                session_factory=session_factory,
                iterations=iterations,
                page=page,
                per_page=per_page,
                search=None,
            ),
            "search": await _run_scenario(
                engine=engine,
                session_factory=session_factory,
                iterations=iterations,
                page=page,
                per_page=per_page,
                search=search,
            ),
        }
    finally:
        await engine.dispose()

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "paths": ["GET /api/v1/persons", "GET /api/v1/persons?search=…"],
        "parameters": {
            "iterations": iterations,
            "page": page,
            "per_page": per_page,
            "search": search,
        },
        "scenarios": scenarios,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--per-page", type=int, default=20)
    parser.add_argument("--search", default="Jan Chryzostom")
    parser.add_argument("--output", type=Path, required=True)
    return parser


async def _run(args: argparse.Namespace) -> None:
    payload = await run_benchmark(
        iterations=args.iterations,
        page=args.page,
        per_page=args.per_page,
        search=args.search,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the person catalogue benchmark and write a JSON evidence artifact."""
    args = _build_parser().parse_args(argv)
    asyncio.run(_run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
