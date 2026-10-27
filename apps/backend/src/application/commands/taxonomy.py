"""Validated application commands for taxonomy reference data."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from src.domain.hagiography.models import (
    ConceptAliasKind,
    ConceptAssignmentStatus,
    PatronageConceptStatus,
)


class CreateCategoryCommand(BaseModel):
    """Input required to create a taxonomy category."""

    name_pl: str = Field(..., min_length=2, max_length=300)
    name_en: str = Field(..., min_length=2, max_length=300)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class CreateTagCommand(BaseModel):
    """Input required to create a taxonomy tag."""

    name_pl: str = Field(..., min_length=2, max_length=200)
    name_en: str = Field(..., min_length=2, max_length=200)
    color: str | None = Field(None, max_length=7, description="Hex color e.g. #FF5733")


class CreatePatronageConceptCommand(BaseModel):
    """Input for a canonical, reviewable patronage concept."""

    patronage_type: str = Field(..., min_length=2, max_length=50)
    name_pl: str = Field(..., min_length=2, max_length=500)
    name_en: str | None = Field(None, max_length=500)
    description: str | None = None


class UpdatePatronageConceptCommand(BaseModel):
    """Editable fields of a patronage concept."""

    patronage_type: str | None = Field(None, min_length=2, max_length=50)
    name_pl: str | None = Field(None, min_length=2, max_length=500)
    name_en: str | None = Field(None, max_length=500)
    description: str | None = None


class CreateConceptAliasCommand(BaseModel):
    """Input for an alternate concept label."""

    value: str = Field(..., min_length=2, max_length=500)
    language_code: str = Field("pl", min_length=2, max_length=10)
    alias_kind: ConceptAliasKind = ConceptAliasKind.COMMON
    source_reference: str | None = None


class CreateConceptAssignmentCommand(BaseModel):
    """Input for assigning a person through a source patronage record."""

    person_id: uuid.UUID
    source_patronage_id: uuid.UUID
    evidence_reference: str = Field(..., min_length=2, max_length=2000)


class ReviewPatronageConceptCommand(BaseModel):
    """Requested lifecycle transition for a concept."""

    target_status: PatronageConceptStatus
    note: str | None = Field(None, max_length=2000)


class ReviewConceptAssignmentCommand(BaseModel):
    """Requested lifecycle transition for a person-to-concept assignment."""

    target_status: ConceptAssignmentStatus
    note: str | None = Field(None, max_length=2000)
