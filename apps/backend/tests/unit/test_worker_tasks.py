"""Unit coverage for Celery configuration and synchronous task wrappers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application import ai_service as ai_service_module
from src.infrastructure.db import session as session_module
from src.workers.celery_app import create_celery_app
from src.workers.tasks.ai import (
    _run_async,
    auto_tag_person,
    batch_auto_tag,
    batch_generate_embeddings,
    generate_person_embedding,
    generate_person_summary,
)
from src.workers.tasks.maintenance import cleanup_expired_tokens, update_statistics


class StubResult:
    def __init__(
        self,
        *,
        scalar: int | None = None,
        ids: list[uuid.UUID] | None = None,
        rows: list[tuple[uuid.UUID]] | None = None,
    ) -> None:
        self.scalar = scalar
        self.ids = ids or []
        self.rows = rows or []

    def scalar_one(self) -> int:
        assert self.scalar is not None
        return self.scalar

    def scalars(self) -> StubResult:
        return self

    def all(self) -> list[uuid.UUID]:
        return self.ids

    def fetchall(self) -> list[tuple[uuid.UUID]]:
        return self.rows


class StubSession:
    def __init__(self, results: list[StubResult] | None = None) -> None:
        self.results = list(results or [])
        self.rollback_count = 0

    async def __aenter__(self) -> StubSession:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, _statement: object) -> StubResult:
        return self.results.pop(0)

    async def rollback(self) -> None:
        self.rollback_count += 1


def _install_session(monkeypatch, session: StubSession) -> None:
    monkeypatch.setattr(session_module, "get_session_factory", lambda: lambda: session)


def test_run_async_and_celery_configuration() -> None:
    async def value() -> str:
        return "ok"

    assert _run_async(value()) == "ok"

    app = create_celery_app()
    assert app.conf.task_routes["src.workers.tasks.ai.*"] == {"queue": "ai"}
    assert app.conf.beat_schedule == {}
    assert app.conf.task_acks_late is True


def test_single_person_ai_tasks(monkeypatch) -> None:
    person_id = uuid.uuid4()
    embedding = SimpleNamespace(
        person_id=person_id,
        canonical_name="Św. Testowy",
        provider="openai",
        model="test-model",
        dimensions=1536,
        was_updated=True,
    )

    class StubAIService:
        embedding_result = embedding
        summary_result: str | None = "Krótkie podsumowanie"

        def __init__(self, _db: object) -> None:
            pass

        async def generate_person_embedding(self, _person_id: uuid.UUID):
            return self.embedding_result

        async def generate_summary(self, _person_id: uuid.UUID, *, max_words: int):
            assert max_words == 25
            return self.summary_result

        async def extract_person_tags(self, _person_id: uuid.UUID) -> list[str]:
            return ["męczennik", "Polska"]

    _install_session(monkeypatch, StubSession())
    monkeypatch.setattr(ai_service_module, "AIService", StubAIService)

    embedding_result = generate_person_embedding.run(str(person_id))
    assert embedding_result == {
        "person_id": str(person_id),
        "canonical_name": "Św. Testowy",
        "provider": "openai",
        "model": "test-model",
        "dimensions": 1536,
        "was_updated": True,
    }

    summary_result = generate_person_summary.run(str(person_id), max_words=25)
    assert summary_result["summary"] == "Krótkie podsumowanie"
    assert summary_result["word_count"] == 2

    tags_result = auto_tag_person.run(str(person_id))
    assert tags_result == {
        "person_id": str(person_id),
        "tags": ["męczennik", "Polska"],
        "count": 2,
    }

    StubAIService.embedding_result = None
    StubAIService.summary_result = None
    assert generate_person_embedding.run(str(person_id)) == {
        "error": f"Person {person_id} not found"
    }
    assert generate_person_summary.run(str(person_id), max_words=25) == {
        "error": f"Person {person_id} not found"
    }


def test_batch_embedding_tracks_processed_skipped_and_failed(monkeypatch) -> None:
    person_ids = [uuid.uuid4() for _ in range(3)]
    session = StubSession(
        [
            StubResult(scalar=3),
            StubResult(ids=person_ids),
            StubResult(ids=[]),
        ]
    )

    class StubAIService:
        def __init__(self, _db: object) -> None:
            pass

        async def generate_person_embedding(self, person_id: uuid.UUID):
            if person_id == person_ids[1]:
                return None
            if person_id == person_ids[2]:
                raise RuntimeError("provider unavailable")
            return SimpleNamespace(person_id=person_id)

    _install_session(monkeypatch, session)
    monkeypatch.setattr(ai_service_module, "AIService", StubAIService)
    update_state = MagicMock()
    monkeypatch.setattr(batch_generate_embeddings, "update_state", update_state)

    result = batch_generate_embeddings.run(batch_size=0, overwrite_existing=False)

    assert result == {"total": 3, "processed": 1, "failed": 1, "skipped": 1}
    assert session.rollback_count == 1
    update_state.assert_called_once_with(
        state="PROGRESS",
        meta={"current": 3, "total": 3, "processed": 1, "failed": 1, "skipped": 1},
    )


def test_batch_auto_tag_reports_progress_and_failures(monkeypatch) -> None:
    person_ids = [uuid.uuid4() for _ in range(10)]
    session = StubSession([StubResult(rows=[(person_id,) for person_id in person_ids])])

    class StubAIService:
        summary_provider = "openai"

        def __init__(self, _db: object) -> None:
            pass

        async def extract_person_tags(self, person_id: uuid.UUID) -> list[str]:
            if person_id == person_ids[4]:
                raise RuntimeError("provider unavailable")
            return ["tag"]

    _install_session(monkeypatch, session)
    monkeypatch.setattr(ai_service_module, "AIService", StubAIService)
    update_state = MagicMock()
    monkeypatch.setattr(batch_auto_tag, "update_state", update_state)

    result = batch_auto_tag.run(only_untagged=False)

    assert result == {"total": 10, "processed": 9, "failed": 1}
    update_state.assert_called_once_with(
        state="PROGRESS",
        meta={"current": 10, "total": 10, "processed": 9},
    )


def test_unimplemented_maintenance_tasks_are_explicitly_disabled() -> None:
    expected = {"status": "disabled", "reason": "not_implemented"}

    assert cleanup_expired_tokens.run() == expected
    assert update_statistics.run() == expected
