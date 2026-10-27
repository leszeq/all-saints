"""Application service for taxonomy reference data."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from src.application.commands.taxonomy import CreateCategoryCommand, CreateTagCommand
from src.application.services.pagination import execute_page
from src.domain.hagiography.models import (
    Category,
    Occupation,
    Patronage,
    Person,
    PublicationStatus,
    StateOfLife,
    Tag,
)


@dataclass(frozen=True, slots=True)
class PatronageConcept:
    """Stable public projection of one existing patronage label.

    The source row remains the authority. Until reviewed concept tables exist,
    a concept is deliberately keyed by its type and exact source label so that
    similarly named records are never silently merged.
    """

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
        """List public patronage concepts without merging source labels."""
        statement = self._patronage_concept_statement(search=search)
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await self.db.execute(count_statement)).scalar_one())
        rows = (
            await self.db.execute(statement.offset((page - 1) * per_page).limit(per_page))
        ).mappings()
        concepts = [
            PatronageConcept(
                slug=patronage_concept_slug(row["patronage_type"], row["name_pl"]),
                patronage_type=row["patronage_type"],
                name_pl=row["name_pl"],
                name_en=row["name_en"],
                description=row["description"],
                person_count=int(row["person_count"]),
            )
            for row in rows
        ]
        return concepts, total

    async def get_patronage_concept(self, slug: str) -> PatronageConcept | None:
        """Resolve one public concept by its deterministic type-qualified slug."""
        statement = self._patronage_concept_statement()
        rows = (await self.db.execute(statement)).mappings()
        for row in rows:
            if patronage_concept_slug(row["patronage_type"], row["name_pl"]) == slug:
                return PatronageConcept(
                    slug=slug,
                    patronage_type=row["patronage_type"],
                    name_pl=row["name_pl"],
                    name_en=row["name_en"],
                    description=row["description"],
                    person_count=int(row["person_count"]),
                )
        return None

    async def list_persons_for_patronage(
        self,
        concept: PatronageConcept,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Person], int]:
        """Return published persons assigned to one exact source concept."""
        filters = (
            Person.deleted_at.is_(None),
            Person.status == PublicationStatus.PUBLISHED.value,
            Patronage.deleted_at.is_(None),
            Patronage.patronage_type == concept.patronage_type,
            Patronage.name_pl == concept.name_pl,
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
    def _patronage_concept_statement(*, search: str | None = None) -> Select[Any]:
        """Build the shared grouped query for public patronage concepts."""
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
