"""PostgreSQL integration coverage for AI application use cases."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.ai_service import AIService
from src.application.ai_suggestions import has_text_value, preview, tag_list
from src.application.services.ai_suggestion_decision_service import (
    AISuggestionDecisionError,
    AISuggestionDecisionService,
)
from src.application.services.person_service import PersonVersionConflictError
from src.domain.hagiography.embedding_model import PersonEmbedding
from src.domain.hagiography.models import (
    Gender,
    Person,
    PersonTag,
    PersonTranslation,
    PersonType,
    PersonVersion,
    PublicationStatus,
    Tag,
)
from src.domain.identity.models import AuditLog
from src.infrastructure.ai.embeddings import (
    VECTOR_DIM,
    BaseEmbeddingProvider,
    DisabledEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingService,
)
from src.infrastructure.ai.summarizer import (
    BaseSummaryProvider,
    ExtractiveSummaryProvider,
    SummaryService,
)


class DeterministicEmbeddingProvider(BaseEmbeddingProvider):
    async def embed(self, text: str) -> list[float]:
        first = min(1.0, max(0.1, len(text) / 1000))
        return [first, *([0.0] * (VECTOR_DIM - 1))]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]

    @property
    def provider_name(self) -> EmbeddingProvider:
        return EmbeddingProvider.OPENAI

    @property
    def model_name(self) -> str:
        return "deterministic-test"

    @property
    def dimensions(self) -> int:
        return VECTOR_DIM


class DeterministicSummaryProvider(BaseSummaryProvider):
    async def summarize(self, text: str, max_words: int = 100) -> str:
        return " ".join(text.split()[:max_words])

    async def extract_tags(self, text: str, person_name: str) -> list[str]:
        return [person_name, "hagiografia"]

    @property
    def provider_name(self) -> str:
        return "deterministic-summary"


def _service(db_session: AsyncSession) -> AIService:
    return AIService(
        db_session,
        embedding_service=EmbeddingService(DeterministicEmbeddingProvider()),
        summary_service=SummaryService(DeterministicSummaryProvider()),
    )


async def _add_person(
    db_session: AsyncSession,
    slug: str,
    *,
    status: PublicationStatus = PublicationStatus.PUBLISHED,
    biography: str | None = "Pełny biogram testowej postaci.",
    ai_summary: str | None = None,
    ai_tags: list[str] | None = None,
    era: str | None = "modern",
) -> Person:
    person = Person(
        id=uuid.uuid4(),
        slug=slug,
        canonical_name=slug.replace("-", " ").title(),
        person_type=PersonType.SAINT.value,
        status=status.value,
        gender=Gender.UNKNOWN.value,
        biography_pl=biography,
        summary_pl="Streszczenie redakcyjne" if biography else None,
        ai_summary=ai_summary,
        ai_tags=ai_tags,
        era=era,
    )
    db_session.add(person)
    await db_session.commit()
    return person


@pytest.mark.asyncio
async def test_ai_writes_wait_for_caller_unit_of_work(
    test_engine,
    db_session: AsyncSession,
) -> None:
    person = await _add_person(db_session, "sw-transakcja-ai")
    person_id = person.id
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as writer_session, session_factory() as observer_session:
        service = _service(writer_session)
        embedding = await service.generate_person_embedding(person_id)
        summary = await service.generate_summary(person_id, max_words=4)
        tags = await service.extract_person_tags(person_id)

        observed_person = (
            await observer_session.execute(select(Person).where(Person.id == person_id))
        ).scalar_one()
        observed_embedding = (
            await observer_session.execute(
                select(PersonEmbedding).where(PersonEmbedding.person_id == person_id)
            )
        ).scalar_one_or_none()
        assert embedding is not None
        assert summary == "Pełny biogram testowej postaci."
        assert tags == [person.canonical_name, "hagiografia"]
        assert observed_person.ai_summary is None
        assert observed_person.ai_tags is None
        assert observed_embedding is None

        await writer_session.commit()
        await observer_session.refresh(observed_person)
        committed_embedding = (
            await observer_session.execute(
                select(PersonEmbedding).where(PersonEmbedding.person_id == person_id)
            )
        ).scalar_one()
        assert observed_person.ai_summary == summary
        assert observed_person.ai_tags == tags
        assert committed_embedding.provider == "openai"


@pytest.mark.asyncio
async def test_embedding_generation_semantic_search_and_related_people(
    db_session: AsyncSession,
) -> None:
    first = await _add_person(db_session, "sw-pierwszy-ai")
    second = await _add_person(db_session, "sw-drugi-ai")
    service = _service(db_session)

    assert await service.generate_person_embedding(uuid.uuid4()) is None
    created = await service.generate_person_embedding(first.id)
    assert created is not None
    assert created.was_updated is False
    assert created.provider == "openai"
    assert created.dimensions == VECTOR_DIM
    assert (await service.generate_person_embedding(second.id)).was_updated is False
    assert (await service.generate_person_embedding(first.id)).was_updated is True

    results = await service.semantic_search(
        "testowa postać",
        limit=5,
        person_type=PersonType.SAINT.value,
        era="modern",
    )
    assert {result.person_id for result in results} == {first.id, second.id}
    assert all(-1 <= result.similarity_score <= 1 for result in results)

    related = await service.find_related(first.id)
    assert [result.person_id for result in related] == [second.id]
    assert await service.find_related(uuid.uuid4()) == []

    status = await service.get_status()
    assert status.total_embeddings == 2
    assert status.coverage_percent == 100.0
    assert status.embedding_provider == "openai"


@pytest.mark.asyncio
async def test_summaries_suggestions_and_admin_dashboard_preserve_editorial_values(
    db_session: AsyncSession,
) -> None:
    ready = await _add_person(
        db_session,
        "gotowy-do-ai",
        status=PublicationStatus.DRAFT,
        biography="Biogram gotowy do opracowania przez moduł sztucznej inteligencji.",
    )
    pending = await _add_person(
        db_session,
        "oczekujacy-na-recenzje-ai",
        ai_summary="Propozycja streszczenia AI",
        ai_tags=["patron chorych", "  ", "miłosierdzie"],
    )
    await _add_person(
        db_session,
        "zarchiwizowany-ai",
        status=PublicationStatus.ARCHIVED,
    )
    empty = await _add_person(
        db_session,
        "bez-biogramu-ai",
        status=PublicationStatus.DRAFT,
        biography=None,
        era=None,
    )
    service = _service(db_session)
    await service.generate_person_embedding(pending.id)

    initial = await service.list_ai_suggestions(limit=20)
    assert initial.pending_review == 2
    assert initial.ready_to_generate >= 3
    assert any(item.id == f"summary:{ready.id}" for item in initial.items)
    assert any(item.id == f"tags:{pending.id}" for item in initial.items)
    assert not any("zarchiwizowany" in item.person_slug for item in initial.items)

    filtered = await service.list_ai_suggestions(
        kind_filter="embedding",
        status_filter="ready_to_generate",
        limit=1,
    )
    assert filtered.total >= 1
    assert len(filtered.items) == 1
    assert filtered.items[0].kind == "embedding"

    summary = await service.generate_summary(ready.id, max_words=4)
    assert summary == "Biogram gotowy do opracowania"
    assert ready.summary_pl == "Streszczenie redakcyjne"
    assert await service.extract_person_tags(ready.id) == [
        ready.canonical_name,
        "hagiografia",
    ]
    assert await service.generate_summary(empty.id) == ""
    assert await service.generate_summary(uuid.uuid4()) is None
    assert await service.extract_person_tags(uuid.uuid4()) == []

    dashboard = await service.get_admin_dashboard()
    assert dashboard.total_persons == 3
    assert dashboard.published_persons == 1
    assert dashboard.total_embeddings == 1
    assert dashboard.missing_embeddings == 2
    assert dashboard.coverage_percent == pytest.approx(33.33)
    assert dashboard.ai_summaries == 2
    assert dashboard.ai_tags == 2
    assert {feature.key for feature in dashboard.feature_statuses} == {
        "embeddings",
        "semantic_search",
        "summaries",
        "tagging",
    }

    disabled = AIService(
        db_session,
        embedding_service=EmbeddingService(DisabledEmbeddingProvider()),
        summary_service=SummaryService(ExtractiveSummaryProvider()),
    )
    blocked = await disabled.list_ai_suggestions(status_filter="blocked", limit=20)
    assert blocked.blocked >= 1
    assert all(item.status == "blocked" for item in blocked.items)


@pytest.mark.asyncio
async def test_ai_suggestions_support_audited_inline_editorial_decisions(
    db_session: AsyncSession,
) -> None:
    person = await _add_person(
        db_session,
        "decyzja-redakcyjna-ai",
        status=PublicationStatus.DRAFT,
        ai_summary="Nowe streszczenie zaproponowane przez AI.",
        ai_tags=["miłosierdzie", "patron chorych"],
    )
    service = AISuggestionDecisionService(db_session)

    summary_decision = await service.decide(
        person.id,
        kind="summary",
        action="accept",
        expected_version=person.version,
        user_id=None,
        value="Streszczenie poprawione i zatwierdzone przez redaktora.",
    )
    assert summary_decision.version == 2
    assert person.summary_pl == "Streszczenie poprawione i zatwierdzone przez redaktora."
    assert person.ai_summary is None
    assert person.status == PublicationStatus.DRAFT.value

    tags_decision = await service.decide(
        person.id,
        kind="tags",
        action="accept",
        expected_version=summary_decision.version,
        user_id=None,
        selected_tags=["miłosierdzie"],
    )
    assert tags_decision.accepted_tags == ["miłosierdzie"]
    assert tags_decision.version == 3
    assert person.ai_tags is None

    linked_tags = list(
        (
            await db_session.execute(
                select(Tag)
                .join(PersonTag, PersonTag.tag_id == Tag.id)
                .where(PersonTag.person_id == person.id)
            )
        )
        .scalars()
        .all()
    )
    assert [tag.name_pl for tag in linked_tags] == ["miłosierdzie"]

    person.ai_summary = "Sugestia, której redaktor nie akceptuje."
    await db_session.flush()
    rejected = await service.decide(
        person.id,
        kind="summary",
        action="reject",
        expected_version=tags_decision.version,
        user_id=None,
        note="Streszczenie pomija kluczowy kontekst źródłowy.",
    )
    await db_session.commit()

    assert rejected.version == 4
    assert person.ai_summary is None
    versions = list(
        (
            await db_session.execute(
                select(PersonVersion)
                .where(PersonVersion.person_id == person.id)
                .order_by(PersonVersion.version_number)
            )
        )
        .scalars()
        .all()
    )
    assert [version.version_number for version in versions] == [2, 3, 4]
    assert versions[1].snapshot["tags"][0]["name_pl"] == "miłosierdzie"
    assert "odrzucono" in (versions[2].change_summary or "")
    audit_rows = list(
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.resource_type == "persons",
                    AuditLog.resource_id == person.id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert [row.extra_metadata["decision"] for row in audit_rows] == [
        "accept",
        "accept",
        "reject",
    ]

    with pytest.raises(PersonVersionConflictError):
        await service.decide(
            person.id,
            kind="summary",
            action="accept",
            expected_version=1,
            user_id=None,
        )
    with pytest.raises(AISuggestionDecisionError, match="uzasadnienia"):
        await service.decide(
            person.id,
            kind="summary",
            action="reject",
            expected_version=person.version,
            user_id=None,
        )


@pytest.mark.asyncio
async def test_approved_ai_summary_is_visible_through_public_localization(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    person = await _add_person(
        db_session,
        "widoczne-streszczenie-ai",
        ai_summary="Nowa publiczna treść zaproponowana przez AI.",
    )
    translation = PersonTranslation(
        person_id=person.id,
        language_code="pl",
        canonical_name=person.canonical_name,
        summary="Nieaktualne streszczenie z tłumaczenia.",
        biography=person.biography_pl,
    )
    db_session.add(translation)
    await db_session.commit()

    result = await AISuggestionDecisionService(db_session).decide(
        person.id,
        kind="summary",
        action="accept",
        expected_version=person.version,
        user_id=None,
        value="Streszczenie zatwierdzone przez redaktora.",
    )
    await db_session.commit()

    response = await async_client.get(f"/api/v1/persons/{person.slug}", params={"locale": "pl"})

    assert response.status_code == 200
    assert response.json()["localized_content"] == {
        "requested_locale": "pl",
        "resolved_locale": "pl",
        "fallback_used": False,
        "source": "translation",
        "canonical_name": person.canonical_name,
        "summary": "Streszczenie zatwierdzone przez redaktora.",
        "biography": person.biography_pl,
        "prayers": None,
        "iconographic_attributes": None,
    }
    await db_session.refresh(translation)
    assert translation.summary == "Streszczenie zatwierdzone przez redaktora."
    assert translation.version == 2
    assert result.version == 2


def test_ai_suggestion_helpers_normalize_previews_and_tags() -> None:
    assert preview("  ") is None
    assert preview("  krótki   tekst ") == "krótki tekst"
    assert preview("abcdefgh", max_length=5) == "abcd…"
    assert tag_list(None) == []
    assert tag_list([" patron ", "", 12]) == ["patron", "12"]
    assert has_text_value(" tekst ") is True
    assert has_text_value(None) is False
