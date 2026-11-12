"""Editorial service for canonical patronage concepts and their evidence links."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from slugify import slugify
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.commands.taxonomy import (
    CreateConceptAliasCommand,
    CreateConceptAssignmentCommand,
    CreatePatronageConceptCommand,
    ReviewConceptAssignmentCommand,
    ReviewPatronageConceptCommand,
    UpdatePatronageConceptCommand,
)
from src.application.services.pagination import execute_page
from src.application.services.person_snapshot import lock_person_for_snapshot
from src.application.services.published_content_guard import (
    require_published_change_permission,
)
from src.domain.hagiography.models import (
    ConceptAlias,
    ConceptAssignmentStatus,
    Patronage,
    PatronageConcept,
    PatronageConceptStatus,
    Person,
    PersonPatronageConcept,
)
from src.domain.hagiography.person_names import normalize_person_name


class ConceptNotFoundError(ValueError):
    """Raised when a concept or assignment target cannot be found."""


class ConceptConflictError(ValueError):
    """Raised when a concept or alias would duplicate an active record."""


class ConceptTransitionError(ValueError):
    """Raised when a requested workflow transition is invalid."""


class ConceptAssignmentError(ValueError):
    """Raised when source evidence cannot support an assignment."""


ALLOWED_CONCEPT_TRANSITIONS: dict[str, set[str]] = {
    PatronageConceptStatus.DRAFT.value: {PatronageConceptStatus.REVIEW.value},
    PatronageConceptStatus.REVIEW.value: {
        PatronageConceptStatus.APPROVED.value,
        PatronageConceptStatus.REJECTED.value,
    },
    PatronageConceptStatus.REJECTED.value: {PatronageConceptStatus.DRAFT.value},
    PatronageConceptStatus.APPROVED.value: {PatronageConceptStatus.REVIEW.value},
}

ALLOWED_ASSIGNMENT_TRANSITIONS: dict[str, set[str]] = {
    ConceptAssignmentStatus.PENDING.value: {
        ConceptAssignmentStatus.APPROVED.value,
        ConceptAssignmentStatus.REJECTED.value,
    },
    ConceptAssignmentStatus.REJECTED.value: {ConceptAssignmentStatus.PENDING.value},
    ConceptAssignmentStatus.APPROVED.value: {ConceptAssignmentStatus.PENDING.value},
}


class ConceptService:
    """Persist concept records while keeping source evidence traceable."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_concepts(
        self,
        *,
        search: str | None = None,
        status: PatronageConceptStatus | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[PatronageConcept], int]:
        """Return one editorial page with aliases and assignments loaded."""
        statement = (
            select(PatronageConcept)
            .options(
                selectinload(PatronageConcept.aliases),
                selectinload(PatronageConcept.assignments),
            )
            .where(PatronageConcept.deleted_at.is_(None))
        )
        if status is not None:
            statement = statement.where(PatronageConcept.status == status.value)
        if search:
            like_term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    PatronageConcept.slug.ilike(like_term),
                    PatronageConcept.patronage_type.ilike(like_term),
                    PatronageConcept.name_pl.ilike(like_term),
                    PatronageConcept.name_en.ilike(like_term),
                )
            )
        return await execute_page(
            self.db,
            statement.order_by(PatronageConcept.name_pl.asc(), PatronageConcept.id.asc()),
            page=page,
            per_page=per_page,
        )

    async def get_concept(self, identifier: str | uuid.UUID) -> PatronageConcept | None:
        """Resolve an active concept by UUID or stable slug."""
        statement = (
            select(PatronageConcept)
            .options(
                selectinload(PatronageConcept.aliases),
                selectinload(PatronageConcept.assignments),
            )
            .where(PatronageConcept.deleted_at.is_(None))
        )
        if isinstance(identifier, uuid.UUID):
            statement = statement.where(PatronageConcept.id == identifier)
        else:
            try:
                statement = statement.where(PatronageConcept.id == uuid.UUID(identifier))
            except ValueError:
                statement = statement.where(PatronageConcept.slug == identifier)
        return (await self.db.execute(statement)).scalar_one_or_none()

    async def create_concept(self, data: CreatePatronageConceptCommand) -> PatronageConcept:
        """Create a draft concept with a type-qualified stable slug."""
        slug = self._build_slug(data.patronage_type, data.name_pl)
        existing = await self.db.scalar(
            select(PatronageConcept).where(
                PatronageConcept.slug == slug,
                PatronageConcept.deleted_at.is_(None),
            )
        )
        if existing is not None:
            raise ConceptConflictError("Pojęcie o takim typie i nazwie już istnieje")
        concept = PatronageConcept(
            slug=slug,
            patronage_type=data.patronage_type.strip(),
            name_pl=data.name_pl.strip(),
            name_en=data.name_en.strip() if data.name_en else None,
            description=data.description.strip() if data.description else None,
            status=PatronageConceptStatus.DRAFT.value,
        )
        self.db.add(concept)
        await self.db.flush()
        return await self._require_concept(concept.id)

    async def update_concept(
        self,
        identifier: str | uuid.UUID,
        data: UpdatePatronageConceptCommand,
    ) -> PatronageConcept:
        """Update editable fields and keep the stable slug deterministic."""
        concept = await self._require_concept(identifier)
        values = data.model_dump(exclude_unset=True)
        if values:
            self._mark_concept_dirty(concept)
        for field in ("patronage_type", "name_pl"):
            if field in values and values[field] is not None:
                values[field] = values[field].strip()
        for field in ("name_en", "description"):
            if field in values and values[field] is not None:
                values[field] = values[field].strip()
        next_type = values.get("patronage_type", concept.patronage_type)
        next_name = values.get("name_pl", concept.name_pl)
        next_slug = self._build_slug(next_type, next_name)
        if next_slug != concept.slug:
            duplicate = await self.db.scalar(
                select(PatronageConcept).where(
                    PatronageConcept.slug == next_slug,
                    PatronageConcept.id != concept.id,
                    PatronageConcept.deleted_at.is_(None),
                )
            )
            if duplicate is not None:
                raise ConceptConflictError("Pojęcie o takim typie i nazwie już istnieje")
            concept.slug = next_slug
        for field, value in values.items():
            setattr(concept, field, value)
        await self.db.flush()
        return await self._require_concept(concept.id)

    async def add_alias(
        self,
        identifier: str | uuid.UUID,
        data: CreateConceptAliasCommand,
    ) -> ConceptAlias:
        """Add a normalized alias to a concept."""
        concept = await self._require_concept(identifier)
        normalized = normalize_person_name(data.value)
        language_code = data.language_code.lower()
        duplicate = await self.db.scalar(
            select(ConceptAlias).where(
                ConceptAlias.concept_id == concept.id,
                ConceptAlias.normalized_value == normalized,
                ConceptAlias.language_code == language_code,
            )
        )
        if duplicate is not None:
            raise ConceptConflictError("Taki alias jest już przypisany do pojęcia")
        alias = ConceptAlias(
            concept_id=concept.id,
            value=data.value.strip(),
            normalized_value=normalized,
            language_code=language_code,
            alias_kind=data.alias_kind.value,
            source_reference=data.source_reference.strip() if data.source_reference else None,
        )
        self.db.add(alias)
        self._mark_concept_dirty(concept)
        await self.db.flush()
        await self.db.refresh(alias)
        return alias

    async def assign_person(
        self,
        identifier: str | uuid.UUID,
        data: CreateConceptAssignmentCommand,
        *,
        user_id: uuid.UUID,
    ) -> PersonPatronageConcept:
        """Create a pending assignment backed by an existing source row."""
        concept = await self._require_concept(identifier)
        person = await self.db.scalar(
            select(Person).where(Person.id == data.person_id, Person.deleted_at.is_(None))
        )
        if person is None:
            raise ConceptAssignmentError("Osoba nie istnieje lub jest usunięta")
        source = await self.db.scalar(
            select(Patronage).where(
                Patronage.id == data.source_patronage_id,
                Patronage.person_id == data.person_id,
                Patronage.deleted_at.is_(None),
            )
        )
        if source is None:
            raise ConceptAssignmentError("Dowód musi wskazywać patronat przypisany do tej osoby")
        existing = await self.db.scalar(
            select(PersonPatronageConcept).where(
                PersonPatronageConcept.person_id == data.person_id,
                PersonPatronageConcept.concept_id == concept.id,
            )
        )
        if existing is not None:
            raise ConceptConflictError("Osoba jest już przypisana do tego pojęcia")
        assignment = PersonPatronageConcept(
            person_id=person.id,
            concept_id=concept.id,
            source_patronage_id=source.id,
            source_patronage_type=source.patronage_type,
            source_label=source.name_pl,
            evidence_reference=data.evidence_reference.strip(),
            status=ConceptAssignmentStatus.PENDING.value,
            assigned_by_id=user_id,
        )
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def transition_concept(
        self,
        identifier: str | uuid.UUID,
        data: ReviewPatronageConceptCommand,
        *,
        user_id: uuid.UUID,
    ) -> PatronageConcept:
        """Apply one allowed concept workflow transition."""
        concept = await self._require_concept(identifier)
        previous = str(concept.status)
        target = data.target_status.value
        if target not in ALLOWED_CONCEPT_TRANSITIONS.get(previous, set()):
            raise ConceptTransitionError(f"Przejście {previous} → {target} nie jest dozwolone")
        note = data.note.strip() if data.note else None
        if target == PatronageConceptStatus.REJECTED.value and not note:
            raise ConceptTransitionError("Odrzucenie pojęcia wymaga komentarza")
        concept.status = target
        concept.reviewed_by_id = user_id
        concept.reviewed_at = datetime.now(UTC)
        concept.review_note = note
        await self.db.flush()
        return await self._require_concept(concept.id)

    async def transition_assignment(
        self,
        concept_identifier: str | uuid.UUID,
        person_id: uuid.UUID,
        data: ReviewConceptAssignmentCommand,
        *,
        user_id: uuid.UUID,
        allow_published_update: bool = False,
    ) -> PersonPatronageConcept:
        """Apply one allowed assignment transition with concept gating."""
        concept = await self._require_concept(concept_identifier)
        assignment = await self.db.scalar(
            select(PersonPatronageConcept).where(
                PersonPatronageConcept.concept_id == concept.id,
                PersonPatronageConcept.person_id == person_id,
            )
        )
        if assignment is None:
            raise ConceptNotFoundError("Przypisanie nie istnieje")
        previous = str(assignment.status)
        target = data.target_status.value
        if target not in ALLOWED_ASSIGNMENT_TRANSITIONS.get(previous, set()):
            raise ConceptTransitionError(f"Przejście {previous} → {target} nie jest dozwolone")
        if target == ConceptAssignmentStatus.APPROVED.value and concept.status != (
            PatronageConceptStatus.APPROVED.value
        ):
            raise ConceptTransitionError("Najpierw zatwierdź pojęcie")
        if target == ConceptAssignmentStatus.APPROVED.value:
            person = await lock_person_for_snapshot(self.db, person_id)
            if person is None:
                raise ConceptAssignmentError("Osoba nie istnieje lub jest usunięta")
            require_published_change_permission(
                person,
                allow_published_update=allow_published_update,
            )
        note = data.note.strip() if data.note else None
        if target == ConceptAssignmentStatus.REJECTED.value and not note:
            raise ConceptTransitionError("Odrzucenie przypisania wymaga komentarza")
        assignment.status = target
        assignment.reviewed_by_id = user_id
        assignment.reviewed_at = datetime.now(UTC)
        assignment.review_note = note
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def _require_concept(self, identifier: str | uuid.UUID) -> PatronageConcept:
        concept = await self.get_concept(identifier)
        if concept is None:
            raise ConceptNotFoundError("Pojęcie nie istnieje")
        return concept

    @staticmethod
    def _build_slug(patronage_type: str, name_pl: str) -> str:
        return slugify(f"{patronage_type.strip()}-{name_pl.strip()}")

    @staticmethod
    def _mark_concept_dirty(concept: PatronageConcept) -> None:
        """Force changed approved metadata back through the review queue."""
        if concept.status != PatronageConceptStatus.DRAFT.value:
            concept.status = PatronageConceptStatus.DRAFT.value
            concept.reviewed_by_id = None
            concept.reviewed_at = None
            concept.review_note = None
