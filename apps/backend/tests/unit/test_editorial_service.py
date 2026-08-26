"""Unit coverage for editorial quality rules and workflow transitions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services import editorial_service as editorial_module
from src.application.services.editorial_service import (
    EditorialService,
    EditorialTransitionError,
)
from src.domain.hagiography.models import PublicationStatus


def make_person(**overrides):
    values = {
        "id": uuid4(),
        "status": PublicationStatus.DRAFT.value,
        "biography_pl": "Biogram",
        "summary_pl": "Streszczenie",
        "birth_year": 1900,
        "death_year": 1980,
        "state_of_life_id": uuid4(),
        "images": [],
        "updated_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_quality_issues_describe_concrete_missing_data():
    person = make_person(
        biography_pl=" ",
        summary_pl=None,
        birth_year=None,
        death_year=None,
        state_of_life_id=None,
    )

    issues = EditorialService._issues(
        person,
        source_count=0,
        image_count=0,
        unknown_license_count=0,
    )

    assert {issue.code for issue in issues} == {
        "missing_biography",
        "missing_summary",
        "missing_sources",
        "missing_image",
        "missing_dates",
        "missing_state_of_life",
    }


def test_completeness_score_has_a_transparent_100_point_breakdown():
    person = make_person(summary_pl="Streszczenie", biography_pl="Biogram")

    criteria = EditorialService._completeness_criteria(
        person,
        source_count=1,
        image_count=1,
        unknown_license_count=0,
    )

    assert sum(criterion.weight for criterion in criteria) == 100
    assert all(criterion.completed for criterion in criteria)
    assert {criterion.key: criterion.weight for criterion in criteria}["sources"] == 15


@pytest.mark.asyncio
async def test_transition_moves_draft_to_review_and_records_editor(monkeypatch):
    person = make_person()
    updated = make_person(
        id=person.id,
        status=PublicationStatus.REVIEW.value,
        updated_at="2026-08-26T10:00:00+00:00",
    )
    person_service = SimpleNamespace(
        get_by_id_or_slug=AsyncMock(return_value=person),
        update_person=AsyncMock(return_value=updated),
    )
    monkeypatch.setattr(editorial_module, "PersonService", lambda _db: person_service)
    editor_id = uuid4()

    result = await EditorialService(SimpleNamespace()).transition(
        person.id,
        PublicationStatus.REVIEW,
        user_id=editor_id,
    )

    assert result.previous_status == PublicationStatus.DRAFT
    assert result.status == PublicationStatus.REVIEW
    update = person_service.update_person.await_args.args[1]
    assert update.status == PublicationStatus.REVIEW
    assert "draft → review" in update.change_summary
    assert person_service.update_person.await_args.kwargs["user_id"] == editor_id


@pytest.mark.asyncio
async def test_transition_rejects_skipping_review(monkeypatch):
    person = make_person()
    person_service = SimpleNamespace(get_by_id_or_slug=AsyncMock(return_value=person))
    monkeypatch.setattr(editorial_module, "PersonService", lambda _db: person_service)

    with pytest.raises(EditorialTransitionError, match="nie jest dozwolone"):
        await EditorialService(SimpleNamespace()).transition(
            person.id,
            PublicationStatus.PUBLISHED,
            user_id=uuid4(),
        )
