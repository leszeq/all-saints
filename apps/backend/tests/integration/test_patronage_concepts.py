"""Integration coverage for reviewable patronage concepts and evidence links."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.taxonomy import (
    CreateConceptAliasCommand,
    CreateConceptAssignmentCommand,
    CreatePatronageConceptCommand,
    ReviewConceptAssignmentCommand,
    ReviewPatronageConceptCommand,
)
from src.application.services.concept_service import ConceptService
from src.application.services.published_content_guard import PublishedContentChangeError
from src.domain.hagiography.models import (
    ConceptAliasKind,
    ConceptAssignmentStatus,
    Gender,
    Patronage,
    PatronageConceptStatus,
    Person,
    PersonType,
    PublicationStatus,
)
from src.domain.identity.models import User, UserStatus


@pytest.mark.asyncio
async def test_concept_workflow_preserves_source_label_and_evidence(
    db_session: AsyncSession,
) -> None:
    person = Person(
        slug="sw-koncept-patronatu",
        canonical_name="Św. Koncept Patronatu",
        person_type=PersonType.SAINT.value,
        status=PublicationStatus.PUBLISHED.value,
        gender=Gender.UNKNOWN.value,
    )
    user = User(
        email="concept-reviewer@example.com",
        hashed_password="not-used-in-service-test",
        full_name="Recenzent pojęć",
        status=UserStatus.ACTIVE.value,
        is_verified=True,
    )
    db_session.add_all([person, user])
    await db_session.flush()
    source = Patronage(
        person_id=person.id,
        patronage_type="profession",
        name_pl="Lekarzy",
        name_en="Doctors",
    )
    db_session.add(source)
    await db_session.flush()

    service = ConceptService(db_session)
    concept = await service.create_concept(
        CreatePatronageConceptCommand(
            patronage_type="profession",
            name_pl="Medycyny",
            name_en="Medicine",
        )
    )
    alias = await service.add_alias(
        concept.id,
        CreateConceptAliasCommand(
            value="Medycyna",
            alias_kind=ConceptAliasKind.COMMON,
            source_reference="Słownik redakcyjny",
        ),
    )
    assignment = await service.assign_person(
        concept.id,
        CreateConceptAssignmentCommand(
            person_id=person.id,
            source_patronage_id=source.id,
            evidence_reference="Bibliografia, s. 42",
        ),
        user_id=user.id,
    )

    assert concept.slug == "profession-medycyny"
    assert alias.normalized_value == "medycyna"
    assert assignment.source_patronage_id == source.id
    assert assignment.source_label == "Lekarzy"
    assert assignment.status == ConceptAssignmentStatus.PENDING.value

    concept = await service.transition_concept(
        concept.id,
        ReviewPatronageConceptCommand(target_status=PatronageConceptStatus.REVIEW),
        user_id=user.id,
    )
    concept = await service.transition_concept(
        concept.id,
        ReviewPatronageConceptCommand(target_status=PatronageConceptStatus.APPROVED),
        user_id=user.id,
    )
    with pytest.raises(PublishedContentChangeError, match="persons:publish"):
        await service.transition_assignment(
            concept.id,
            person.id,
            ReviewConceptAssignmentCommand(target_status=ConceptAssignmentStatus.APPROVED),
            user_id=user.id,
        )
    assignment = await service.transition_assignment(
        concept.id,
        person.id,
        ReviewConceptAssignmentCommand(target_status=ConceptAssignmentStatus.APPROVED),
        user_id=user.id,
        allow_published_update=True,
    )

    assert concept.status == PatronageConceptStatus.APPROVED.value
    assert assignment.status == ConceptAssignmentStatus.APPROVED.value
    assert assignment.evidence_reference == "Bibliografia, s. 42"
