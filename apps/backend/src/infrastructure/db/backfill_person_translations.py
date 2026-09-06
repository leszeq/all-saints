"""CLI for the explicit legacy-column to PersonTranslation migration."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from src.application.services.person_translation_backfill import (
    PersonTranslationBackfillResult,
    PersonTranslationBackfillService,
)
from src.domain.geography import models as geography_models  # noqa: F401
from src.domain.hagiography import embedding_model as embedding_models  # noqa: F401
from src.domain.identity import models as identity_models  # noqa: F401
from src.domain.liturgy import models as liturgy_models  # noqa: F401
from src.domain.sources import models as source_models  # noqa: F401
from src.infrastructure.db.session import get_session_factory


async def backfill_person_translations(
    *,
    apply: bool = False,
    batch_size: int = 500,
) -> PersonTranslationBackfillResult:
    """Own the transaction used by the standalone maintenance command."""
    session_factory = get_session_factory()
    async with session_factory() as session, session.begin():
        return await PersonTranslationBackfillService(session).run(
            apply=apply,
            batch_size=batch_size,
        )


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill pl/en PersonTranslation rows from legacy person columns"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist unambiguous missing rows; omission performs a read-only dry run",
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fail-on-conflict", action="store_true")
    args = parser.parse_args()

    result = await backfill_person_translations(
        apply=args.apply,
        batch_size=args.batch_size,
    )
    serialized = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")

    if args.fail_on_conflict and result.conflicts:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(_main())
