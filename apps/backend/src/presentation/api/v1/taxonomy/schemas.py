"""
Pydantic v2 schemas for Taxonomy (Category, Tag, StateOfLife, Occupation).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.taxonomy import CreateCategoryCommand, CreateTagCommand

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
