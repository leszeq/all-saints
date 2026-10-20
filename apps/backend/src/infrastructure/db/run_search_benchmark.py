"""Read-only adapter that exports public person-search results for the benchmark."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.application.search_benchmark import load_search_benchmark
from src.application.services.person_query_service import PersonQueryService
from src.domain.geography import models as _geography_models  # noqa: F401
from src.domain.hagiography import embedding_model as _embedding_model  # noqa: F401
from src.domain.hagiography import models as _hagiography_models  # noqa: F401
from src.domain.sources import models as _source_models  # noqa: F401
from src.infrastructure.db.session import get_engine


async def collect_search_results(fixture_path: Path) -> dict[str, Any]:
    """Execute every fixture query against published records and return JSON data."""
    fixture = load_search_benchmark(fixture_path)
    engine = get_engine()
    ranked_results: dict[str, list[str]] = {}
    reasons: dict[str, list[dict[str, str | None]]] = {}
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            service = PersonQueryService(session)
            for case in fixture.cases:
                persons, _ = await service.list_persons(
                    search=case.query,
                    published_only=True,
                    per_page=fixture.cutoff,
                )
                ranked_results[case.case_id] = [person.slug for person in persons]
                reasons[case.case_id] = [
                    {
                        "slug": person.slug,
                        "reason": getattr(person, "search_reason", None),
                        "match": getattr(person, "search_match", None),
                    }
                    for person in persons
                ]
    finally:
        await engine.dispose()
    return {"results": ranked_results, "reasons": reasons}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


async def _run(args: argparse.Namespace) -> None:
    payload = await collect_search_results(args.fixture)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Export benchmark results without mutating the database."""
    args = _build_parser().parse_args(argv)
    asyncio.run(_run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
