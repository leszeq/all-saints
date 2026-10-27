"""
Pydantic v2 schemas for Taxonomy (Category, Tag, StateOfLife, Occupation).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.taxonomy import (
    CreateCategoryCommand,
    CreateConceptAliasCommand,
    CreateConceptAssignmentCommand,
    CreatePatronageConceptCommand,
    CreateTagCommand,
    ReviewConceptAssignmentCommand,
    ReviewPatronageConceptCommand,
    UpdatePatronageConceptCommand,
)
from src.domain.hagiography.models import (
    ConceptAliasKind,
    ConceptAssignmentStatus,
    PatronageConceptStatus,
    PersonType,
)

# ==============================================================================
# CATEGORY SCHEMAS
# ==============================================================================


class CategoryCreateSchema(CreateCategoryCommand):
    pass


class CategoryUpdateSchema(BaseModel):
    name_pl: str | None = Field(None, min_length=2, max_length=300)
    name_en: str | None = Field(None, min_length=2, max_length=300)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int | None = None


class CategorySchema(CategoryCreateSchema):
    id: uuid.UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# TAG SCHEMAS
# ==============================================================================


class TagCreateSchema(CreateTagCommand):
    pass


class TagUpdateSchema(BaseModel):
    name_pl: str | None = Field(None, min_length=2, max_length=200)
    name_en: str | None = Field(None, min_length=2, max_length=200)
    color: str | None = None


class TagSchema(TagCreateSchema):
    id: uuid.UUID
    slug: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# STATE OF LIFE SCHEMAS
# ==============================================================================


class StateOfLifeSchema(BaseModel):
    id: uuid.UUID
    name_pl: str
    name_en: str
    name_la: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# OCCUPATION SCHEMAS
# ==============================================================================


class OccupationSchema(BaseModel):
    id: uuid.UUID
    name_pl: str
    name_en: str
    name_la: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PatronageConceptSchema(BaseModel):
    """A type-qualified public patronage concept."""

    slug: str
    patronage_type: str
    name_pl: str
    name_en: str | None = None
    description: str | None = None
    person_count: int = Field(ge=0)


class ConceptAliasSchema(BaseModel):
    """Editorial alias attached to a canonical patronage concept."""

    id: uuid.UUID
    concept_id: uuid.UUID
    value: str
    normalized_value: str
    language_code: str
    alias_kind: ConceptAliasKind
    source_reference: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatronageConceptManagementSchema(BaseModel):
    """Admin projection of a reviewable patronage concept."""

    id: uuid.UUID
    slug: str
    patronage_type: str
    name_pl: str
    name_en: str | None = None
    description: str | None = None
    status: PatronageConceptStatus
    reviewed_by_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    aliases: list[ConceptAliasSchema] = Field(default_factory=list)
    assignment_count: int = Field(default=0, ge=0)
    person_count: int = Field(default=0, ge=0)

    model_config = ConfigDict(from_attributes=True)


class PatronageConceptCreateSchema(CreatePatronageConceptCommand):
    pass


class PatronageConceptUpdateSchema(UpdatePatronageConceptCommand):
    pass


class ConceptAliasCreateSchema(CreateConceptAliasCommand):
    pass


class ConceptAssignmentCreateSchema(CreateConceptAssignmentCommand):
    pass


class PatronageConceptReviewSchema(ReviewPatronageConceptCommand):
    pass


class ConceptAssignmentReviewSchema(ReviewConceptAssignmentCommand):
    pass


class PersonPatronageConceptSchema(BaseModel):
    """Admin projection of a person-to-concept evidence assignment."""

    person_id: uuid.UUID
    concept_id: uuid.UUID
    source_patronage_id: uuid.UUID | None = None
    source_patronage_type: str
    source_label: str
    evidence_reference: str
    status: ConceptAssignmentStatus
    assigned_by_id: uuid.UUID | None = None
    reviewed_by_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PatronageConceptPersonSchema(BaseModel):
    """Small public person projection used on a patronage concept page."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    canonical_name_en: str | None = None
    person_type: PersonType
    summary_pl: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PatronageConceptPersonsSchema(BaseModel):
    """Paginated people assigned to one public patronage concept."""

    concept: PatronageConceptSchema
    items: list[PatronageConceptPersonSchema]
    total: int
    page: int
    per_page: int
    pages: int
