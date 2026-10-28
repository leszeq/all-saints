"""Application service for taxonomy reference data."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from slugify import slugify
from sqlalchemy import func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from src.application.commands.taxonomy import CreateCategoryCommand, CreateTagCommand
from src.application.services.pagination import execute_page
from src.domain.hagiography.models import (
    Category,
    ConceptAlias,
    ConceptAssignmentStatus,
    Occupation,
    Patronage,
    PatronageConceptStatus,
    Person,
    PersonPatronageConcept,
    PublicationStatus,
    StateOfLife,
    Tag,
)
from src.domain.hagiography.models import (
    PatronageConcept as PatronageConceptModel,
)


@dataclass(frozen=True, slots=True)
class PatronageConcept:
    """Stable public projection of one canonical or source-backed concept."""

    slug: str
    patronage_type: str
    name_pl: str
    name_en: str | None
    description: str | None
    person_count: int


def patronage_concept_slug(patronage_type: str, name_pl: str) -> str:
    """Build a deterministic, type-qualified slug for a public concept."""
    return slugify(f"{patronage_type}-{name_pl}")


class TaxonomyService:
    """Read and create taxonomy records inside a caller-owned transaction."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_categories(
        self,
        *,
        parent_id: uuid.UUID | None = None,
    ) -> list[Category]:
        """Return active categories in editorial display order."""
        statement = select(Category).where(Category.deleted_at.is_(None))
        if parent_id is not None:
            statement = statement.where(Category.parent_id == parent_id)
        result = await self.db.execute(
            statement.order_by(Category.sort_order.asc(), Category.name_pl.asc())
        )
        return list(result.scalars().all())

    async def create_category(self, data: CreateCategoryCommand) -> Category:
        """Create a category with a deterministic slug."""
        category = Category(slug=slugify(data.name_pl), **data.model_dump())
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def list_tags(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Tag], int]:
        """Return one filtered page of active tags."""
        statement = select(Tag).where(Tag.deleted_at.is_(None))
        if search:
            statement = statement.where(
                Tag.name_pl.ilike(f"%{search}%") | Tag.name_en.ilike(f"%{search}%")
            )
        return await execute_page(
            self.db,
            statement.order_by(Tag.name_pl.asc()),
            page=page,
            per_page=per_page,
        )

    async def create_tag(self, data: CreateTagCommand) -> Tag:
        """Create a tag with a deterministic slug."""
        tag = Tag(slug=slugify(data.name_pl), **data.model_dump())
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        return tag

    async def list_states_of_life(self) -> list[StateOfLife]:
        """Return the complete active state-of-life dictionary."""
        statement = (
            select(StateOfLife)
            .where(StateOfLife.deleted_at.is_(None))
            .order_by(StateOfLife.name_pl.asc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def list_occupations(
        self,
        *,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[Occupation], int]:
        """Return one page of active occupations."""
        statement = (
            select(Occupation)
            .where(Occupation.deleted_at.is_(None))
            .order_by(Occupation.name_pl.asc())
        )
        return await execute_page(self.db, statement, page=page, per_page=per_page)

    async def list_patronage_concepts(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> tuple[list[PatronageConcept], int]:
        """List reviewed concepts and keep unmapped legacy labels discoverable.

        Reviewed assignments become the public authority as soon as both the
        concept and its person relation are approved. Source rows without an
        approved mapping continue to use the previous exact-label projection,
        which makes the migration incremental and prevents disappearing data.
        """
        reviewed = await self._list_approved_patronage_concepts(search=search)
        legacy = await self._list_legacy_patronage_concepts(search=search)

        merged = {(concept.patronage_type, concept.name_pl): concept for concept in legacy}
        for concept in reviewed:
            key = (concept.patronage_type, concept.name_pl)
            previous = merged.get(key)
            if previous is not None:
                concept = PatronageConcept(
                    slug=concept.slug,
                    patronage_type=concept.patronage_type,
                    name_pl=concept.name_pl,
                    name_en=concept.name_en,
                    description=concept.description,
                    person_count=concept.person_count + previous.person_count,
                )
            merged[key] = concept
        concepts = sorted(
            merged.values(),
            key=lambda concept: (concept.name_pl, concept.patronage_type, concept.slug),
        )
        total = len(concepts)
        start = (page - 1) * per_page
        return concepts[start : start + per_page], total

    async def get_patronage_concept(self, slug: str) -> PatronageConcept | None:
        """Resolve one reviewed concept, then fall back to a source label."""
        reviewed_statement = self._approved_patronage_concept_statement()
        reviewed_rows = (
            await self.db.execute(reviewed_statement.where(PatronageConceptModel.slug == slug))
        ).mappings()
        reviewed_row = next(iter(reviewed_rows), None)
        if reviewed_row is not None:
            return self._concept_from_row(reviewed_row)

        statement = self._legacy_patronage_concept_statement()
        rows = (await self.db.execute(statement)).mappings()
        for row in rows:
            if patronage_concept_slug(row["patronage_type"], row["name_pl"]) == slug:
                return self._concept_from_row(row)

        mapped_source_statement = (
            select(
                PatronageConceptModel.slug.label("concept_slug"),
                Patronage.patronage_type.label("patronage_type"),
                Patronage.name_pl.label("name_pl"),
            )
            .join(
                PersonPatronageConcept,
                PersonPatronageConcept.concept_id == PatronageConceptModel.id,
            )
            .join(Patronage, Patronage.id == PersonPatronageConcept.source_patronage_id)
            .join(Person, Person.id == PersonPatronageConcept.person_id)
            .where(
                PatronageConceptModel.deleted_at.is_(None),
                PatronageConceptModel.status == PatronageConceptStatus.APPROVED.value,
                PersonPatronageConcept.status == ConceptAssignmentStatus.APPROVED.value,
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
                Patronage.deleted_at.is_(None),
            )
            .distinct()
        )
        mapped_source_rows = (await self.db.execute(mapped_source_statement)).mappings()
        for mapped_source in mapped_source_rows:
            if (
                patronage_concept_slug(mapped_source["patronage_type"], mapped_source["name_pl"])
                != slug
            ):
                continue
            reviewed_rows = (
                await self.db.execute(
                    reviewed_statement.where(
                        PatronageConceptModel.slug == mapped_source["concept_slug"]
                    )
                )
            ).mappings()
            reviewed_row = next(iter(reviewed_rows), None)
            if reviewed_row is not None:
                return self._concept_from_row(reviewed_row)
        return None

    async def list_persons_for_patronage(
        self,
        concept: PatronageConcept,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Person], int]:
        """Return people from reviewed assignments or exact source labels."""
        reviewed_concept = await self._approved_concept_model_by_slug(concept.slug)
        if reviewed_concept is not None:
            assignment_filters = (
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
                PersonPatronageConcept.concept_id == reviewed_concept.id,
                PersonPatronageConcept.status == ConceptAssignmentStatus.APPROVED.value,
            )
            statement = (
                select(Person)
                .join(PersonPatronageConcept, PersonPatronageConcept.person_id == Person.id)
                .options(selectinload(Person.patronages))
                .where(*assignment_filters)
                .distinct()
                .order_by(Person.canonical_name.asc(), Person.id.asc())
            )
            reviewed_persons = list((await self.db.execute(statement)).scalars().unique().all())

            source_filters = (
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
                Patronage.deleted_at.is_(None),
                Patronage.patronage_type == concept.patronage_type,
                Patronage.name_pl == concept.name_pl,
                self._unreviewed_patronage_filter(),
            )
            source_statement = (
                select(Person)
                .join(Patronage, Patronage.person_id == Person.id)
                .options(selectinload(Person.patronages))
                .where(*source_filters)
                .distinct()
                .order_by(Person.canonical_name.asc(), Person.id.asc())
            )
            source_persons = list(
                (await self.db.execute(source_statement)).scalars().unique().all()
            )
            persons_by_id = {person.id: person for person in reviewed_persons}
            persons_by_id.update({person.id: person for person in source_persons})
            persons = sorted(
                persons_by_id.values(),
                key=lambda person: (person.canonical_name, person.id),
            )
            total = len(persons)
            start = (page - 1) * per_page
            return persons[start : start + per_page], total

        filters = (
            Person.deleted_at.is_(None),
            Person.status == PublicationStatus.PUBLISHED.value,
            Patronage.deleted_at.is_(None),
            Patronage.patronage_type == concept.patronage_type,
            Patronage.name_pl == concept.name_pl,
            self._unreviewed_patronage_filter(),
        )
        count_statement = (
            select(func.count(func.distinct(Person.id)))
            .select_from(Person)
            .join(Patronage, Patronage.person_id == Person.id)
            .where(*filters)
        )
        total = int((await self.db.execute(count_statement)).scalar_one())
        statement = (
            select(Person)
            .join(Patronage, Patronage.person_id == Person.id)
            .options(selectinload(Person.patronages))
            .where(*filters)
            .distinct()
            .order_by(Person.canonical_name.asc(), Person.id.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        persons = list((await self.db.execute(statement)).scalars().unique().all())
        return persons, total

    @staticmethod
    def _concept_from_row(row: RowMapping) -> PatronageConcept:
        """Build the stable public projection from either grouped query."""
        return PatronageConcept(
            slug=(
                row["slug"]
                if "slug" in row
                else patronage_concept_slug(row["patronage_type"], row["name_pl"])
            ),
            patronage_type=row["patronage_type"],
            name_pl=row["name_pl"],
            name_en=row["name_en"],
            description=row["description"],
            person_count=int(row["person_count"]),
        )

    @staticmethod
    def _unreviewed_patronage_filter() -> ColumnElement[bool]:
        """Exclude source rows already represented by an approved assignment."""
        return (
            ~select(1)
            .select_from(PersonPatronageConcept)
            .join(
                PatronageConceptModel,
                PatronageConceptModel.id == PersonPatronageConcept.concept_id,
            )
            .where(
                PersonPatronageConcept.person_id == Patronage.person_id,
                PersonPatronageConcept.source_patronage_id == Patronage.id,
                PersonPatronageConcept.status == ConceptAssignmentStatus.APPROVED.value,
                PatronageConceptModel.status == PatronageConceptStatus.APPROVED.value,
                PatronageConceptModel.deleted_at.is_(None),
            )
            .exists()
        )

    async def _list_approved_patronage_concepts(
        self, *, search: str | None = None
    ) -> list[PatronageConcept]:
        rows = (
            await self.db.execute(self._approved_patronage_concept_statement(search=search))
        ).mappings()
        return [self._concept_from_row(row) for row in rows]

    async def _list_legacy_patronage_concepts(
        self, *, search: str | None = None
    ) -> list[PatronageConcept]:
        rows = (
            await self.db.execute(self._legacy_patronage_concept_statement(search=search))
        ).mappings()
        return [self._concept_from_row(row) for row in rows]

    async def _approved_concept_model_by_slug(self, slug: str) -> PatronageConceptModel | None:
        statement = (
            select(PatronageConceptModel)
            .join(
                PersonPatronageConcept,
                PersonPatronageConcept.concept_id == PatronageConceptModel.id,
            )
            .join(Person, Person.id == PersonPatronageConcept.person_id)
            .where(
                PatronageConceptModel.slug == slug,
                PatronageConceptModel.deleted_at.is_(None),
                PatronageConceptModel.status == PatronageConceptStatus.APPROVED.value,
                PersonPatronageConcept.status == ConceptAssignmentStatus.APPROVED.value,
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
            )
            .limit(1)
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    @staticmethod
    def _approved_patronage_concept_statement(*, search: str | None = None) -> Select[Any]:
        """Build the grouped query for concepts visible after review."""
        statement = (
            select(
                PatronageConceptModel.slug.label("slug"),
                PatronageConceptModel.patronage_type.label("patronage_type"),
                PatronageConceptModel.name_pl.label("name_pl"),
                PatronageConceptModel.name_en.label("name_en"),
                PatronageConceptModel.description.label("description"),
                func.count(func.distinct(Person.id)).label("person_count"),
            )
            .join(
                PersonPatronageConcept,
                PersonPatronageConcept.concept_id == PatronageConceptModel.id,
            )
            .join(Person, Person.id == PersonPatronageConcept.person_id)
            .where(
                PatronageConceptModel.deleted_at.is_(None),
                PatronageConceptModel.status == PatronageConceptStatus.APPROVED.value,
                PersonPatronageConcept.status == ConceptAssignmentStatus.APPROVED.value,
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
            )
            .group_by(
                PatronageConceptModel.slug,
                PatronageConceptModel.patronage_type,
                PatronageConceptModel.name_pl,
                PatronageConceptModel.name_en,
                PatronageConceptModel.description,
            )
            .order_by(
                PatronageConceptModel.name_pl.asc(),
                PatronageConceptModel.patronage_type.asc(),
            )
        )
        if search:
            like_term = f"%{search.strip()}%"
            alias_match = select(1).where(
                ConceptAlias.concept_id == PatronageConceptModel.id,
                ConceptAlias.deleted_at.is_(None),
                or_(
                    ConceptAlias.value.ilike(like_term),
                    ConceptAlias.normalized_value.ilike(like_term),
                ),
            )
            statement = statement.where(
                or_(
                    PatronageConceptModel.slug.ilike(like_term),
                    PatronageConceptModel.patronage_type.ilike(like_term),
                    PatronageConceptModel.name_pl.ilike(like_term),
                    PatronageConceptModel.name_en.ilike(like_term),
                    alias_match.exists(),
                )
            )
        return statement

    @staticmethod
    def _legacy_patronage_concept_statement(*, search: str | None = None) -> Select[Any]:
        """Build the grouped fallback query for source rows without review."""
        statement = (
            select(
                Patronage.patronage_type.label("patronage_type"),
                Patronage.name_pl.label("name_pl"),
                func.min(Patronage.name_en).label("name_en"),
                func.min(Patronage.description).label("description"),
                func.count(func.distinct(Patronage.person_id)).label("person_count"),
            )
            .join(Person, Person.id == Patronage.person_id)
            .where(
                Patronage.deleted_at.is_(None),
                Person.deleted_at.is_(None),
                Person.status == PublicationStatus.PUBLISHED.value,
                TaxonomyService._unreviewed_patronage_filter(),
            )
            .group_by(Patronage.patronage_type, Patronage.name_pl)
            .order_by(Patronage.name_pl.asc(), Patronage.patronage_type.asc())
        )
        if search:
            like_term = f"%{search.strip()}%"
            statement = statement.where(
                Patronage.name_pl.ilike(like_term)
                | Patronage.name_en.ilike(like_term)
                | Patronage.patronage_type.ilike(like_term)
            )
        return statement
