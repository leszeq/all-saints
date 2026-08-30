"""
AI Celery Tasks.

Background tasks for AI-powered processing:
- generate_person_embedding: Generate/refresh vector embedding for one person
- batch_generate_embeddings: Bulk embedding generation for all persons
- generate_person_summary: AI biography summarization
- auto_tag_person: AI-powered tag extraction
- batch_auto_tag: Bulk tagging for all persons without tags
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any, TypeVar

from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy import func, select

from src.workers.task_decorators import typed_shared_task

logger = get_task_logger(__name__)
T = TypeVar("T")


# ==============================================================================
# HELPERS
# ==============================================================================


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async code in Celery worker (sync context)."""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ==============================================================================
# SINGLE PERSON EMBEDDING
# ==============================================================================


@typed_shared_task(
    name="src.workers.tasks.ai.generate_person_embedding",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="ai",
)
def generate_person_embedding(self: Task, person_id: str) -> dict[str, Any]:
    """
    Generate or refresh the semantic embedding for a single person.

    Args:
        person_id: UUID string of the person.

    Returns:
        Dict with embedding metadata.
    """
    logger.info(f"Generating embedding for person {person_id}")

    async def _run() -> dict[str, Any]:
        from src.application.ai_service import AIService
        from src.infrastructure.db.session import get_session_factory

        pid = uuid.UUID(person_id)
        session_factory = get_session_factory()

        async with session_factory() as db:
            service = AIService(db)
            result = await service.generate_person_embedding(pid)

            if result is None:
                return {"error": f"Person {person_id} not found"}

            return {
                "person_id": str(result.person_id),
                "canonical_name": result.canonical_name,
                "provider": result.provider,
                "model": result.model,
                "dimensions": result.dimensions,
                "was_updated": result.was_updated,
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"Embedding generation failed for {person_id}: {exc}")
        raise self.retry(exc=exc) from exc


# ==============================================================================
# BATCH EMBEDDING
# ==============================================================================


@typed_shared_task(
    name="src.workers.tasks.ai.batch_generate_embeddings",
    bind=True,
    max_retries=1,
    queue="ai",
    time_limit=3600,  # 1 hour max
)
def batch_generate_embeddings(
    self: Task,
    batch_size: int = 50,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    """
    Batch generate embeddings for all persons without embeddings (or all if overwrite=True).

    This task processes persons in batches to avoid memory issues.
    Progress is stored in Celery task state.

    Args:
        batch_size: Number of persons to process per DB query.
        overwrite_existing: If True, regenerate even existing embeddings.

    Returns:
        Summary dict with counts.
    """
    batch_size = max(1, batch_size)
    logger.info(
        f"Starting batch embedding generation "
        f"(batch_size={batch_size}, overwrite={overwrite_existing})"
    )

    async def _run() -> dict[str, Any]:
        from src.application.ai_service import AIService
        from src.domain.hagiography.embedding_model import PersonEmbedding
        from src.domain.hagiography.models import Person
        from src.infrastructure.db.session import get_session_factory

        processed = 0
        failed = 0
        skipped = 0

        async with get_session_factory()() as db:
            service = AIService(db)

            # Build a stable base query and fetch IDs in bounded keyset pages.
            if overwrite_existing:
                base_stmt = select(Person.id).where(Person.deleted_at.is_(None))
            else:
                # Only persons without embeddings
                base_stmt = (
                    select(Person.id)
                    .where(Person.deleted_at.is_(None))
                    .outerjoin(PersonEmbedding, PersonEmbedding.person_id == Person.id)
                    .where(PersonEmbedding.id.is_(None))
                )

            count_result = await db.execute(select(func.count()).select_from(base_stmt.subquery()))
            total = int(count_result.scalar_one())

            logger.info(f"Found {total} persons to embed")

            last_id: uuid.UUID | None = None
            current = 0

            while True:
                page_stmt = base_stmt.order_by(Person.id).limit(batch_size)
                if last_id is not None:
                    page_stmt = page_stmt.where(Person.id > last_id)

                page_result = await db.execute(page_stmt)
                person_ids = list(page_result.scalars().all())
                if not person_ids:
                    break

                last_id = person_ids[-1]
                for person_id in person_ids:
                    try:
                        embedding_result = await service.generate_person_embedding(person_id)
                        if embedding_result:
                            processed += 1
                        else:
                            skipped += 1
                    except Exception as exc:
                        await db.rollback()
                        logger.error(f"Failed to embed person {person_id}: {exc}")
                        failed += 1

                    current += 1
                    if current % 10 == 0 or current == total:
                        self.update_state(
                            state="PROGRESS",
                            meta={
                                "current": current,
                                "total": total,
                                "processed": processed,
                                "failed": failed,
                                "skipped": skipped,
                            },
                        )
                        logger.info(
                            f"Progress: {current}/{total} "
                            f"(processed={processed}, failed={failed})"
                        )

        return {
            "total": total,
            "processed": processed,
            "failed": failed,
            "skipped": skipped,
        }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"Batch embedding failed: {exc}")
        raise self.retry(exc=exc) from exc


# ==============================================================================
# BIOGRAPHY SUMMARIZATION
# ==============================================================================


@typed_shared_task(
    name="src.workers.tasks.ai.generate_person_summary",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ai",
)
def generate_person_summary(
    self: Task,
    person_id: str,
    max_words: int = 100,
) -> dict[str, Any]:
    """
    Generate AI summary for a person's biography.

    Args:
        person_id: UUID string of the person.
        max_words: Target summary length.

    Returns:
        Dict with generated summary.
    """
    logger.info(f"Generating summary for person {person_id}")

    async def _run() -> dict[str, Any]:
        from src.application.ai_service import AIService
        from src.infrastructure.db.session import get_session_factory

        pid = uuid.UUID(person_id)

        async with get_session_factory()() as db:
            service = AIService(db)
            summary = await service.generate_summary(pid, max_words=max_words)

            if summary is None:
                return {"error": f"Person {person_id} not found"}

            return {
                "person_id": person_id,
                "summary": summary,
                "word_count": len(summary.split()) if summary else 0,
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"Summary generation failed for {person_id}: {exc}")
        raise self.retry(exc=exc) from exc


# ==============================================================================
# AUTO-TAGGING
# ==============================================================================


@typed_shared_task(
    name="src.workers.tasks.ai.auto_tag_person",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="ai",
)
def auto_tag_person(self: Task, person_id: str) -> dict[str, Any]:
    """
    Extract tags from a person's biography using AI.

    Args:
        person_id: UUID string of the person.

    Returns:
        Dict with extracted tags.
    """
    logger.info(f"Auto-tagging person {person_id}")

    async def _run() -> dict[str, Any]:
        from src.application.ai_service import AIService
        from src.infrastructure.db.session import get_session_factory

        pid = uuid.UUID(person_id)

        async with get_session_factory()() as db:
            service = AIService(db)
            tags = await service.extract_person_tags(pid)

            return {
                "person_id": person_id,
                "tags": tags,
                "count": len(tags),
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"Auto-tagging failed for {person_id}: {exc}")
        raise self.retry(exc=exc) from exc


# ==============================================================================
# BATCH AUTO-TAGGING
# ==============================================================================


@typed_shared_task(
    name="src.workers.tasks.ai.batch_auto_tag",
    bind=True,
    max_retries=1,
    queue="ai",
    time_limit=7200,  # 2 hours max
)
def batch_auto_tag(self: Task, only_untagged: bool = True) -> dict[str, Any]:
    """
    Auto-tag all persons (or only those without ai_tags).

    Args:
        only_untagged: If True, skip persons that already have ai_tags.

    Returns:
        Summary dict.
    """
    logger.info(f"Starting batch auto-tag (only_untagged={only_untagged})")

    async def _run() -> dict[str, Any]:
        from src.application.ai_service import AIService
        from src.domain.hagiography.models import Person
        from src.infrastructure.db.session import get_session_factory

        processed = 0
        failed = 0

        async with get_session_factory()() as db:
            service = AIService(db)
            if service.summary_provider == "extractive-fallback":
                raise RuntimeError("Automatyczne tagowanie AI jest wyłączone")

            stmt = select(Person.id).where(Person.deleted_at.is_(None))
            if only_untagged:
                stmt = stmt.where(Person.ai_tags.is_(None))

            result = await db.execute(stmt)
            all_ids = [row[0] for row in result.fetchall()]
            total = len(all_ids)

            for i, person_id in enumerate(all_ids):
                try:
                    await service.extract_person_tags(person_id)
                    processed += 1
                except Exception as exc:
                    logger.error(f"Failed to tag person {person_id}: {exc}")
                    failed += 1

                if (i + 1) % 10 == 0:
                    self.update_state(
                        state="PROGRESS",
                        meta={"current": i + 1, "total": total, "processed": processed},
                    )

        return {"total": total, "processed": processed, "failed": failed}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.error(f"Batch auto-tag failed: {exc}")
        raise self.retry(exc=exc) from exc
