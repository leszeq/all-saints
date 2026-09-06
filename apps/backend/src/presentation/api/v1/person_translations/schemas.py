"""HTTP response contracts for person translations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.hagiography.models import PublicationStatus


class PersonTranslationSchema(BaseModel):
    """One active localized-content row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    language_code: str
    canonical_name: str | None
    summary: str | None
    biography: str | None
    prayers: str | None
    iconographic_attributes: str | None
    translated_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    version: int


class PersonTranslationMutationSchema(PersonTranslationSchema):
    """Changed translation with its new parent revision."""

    person_version: int


class PersonTranslationListSchema(BaseModel):
    """All active locales and the editorial state they belong to."""

    items: list[PersonTranslationSchema]
    person_version: int
    person_status: PublicationStatus


class PersonTranslationDeleteSchema(BaseModel):
    """Deletion acknowledgement used to continue optimistic locking."""

    language_code: str
    person_version: int
