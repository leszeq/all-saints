"""Schemas for the editorial dashboard and review queue."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from src.domain.hagiography.models import PublicationStatus
from src.presentation.api.v1.persons.schemas import (
    PersonAvatarSchema,
    PersonLastEditorSchema,
)


class EditorialPriority(StrEnum):
    """Operational priority computed from workflow state and data gaps."""

    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"


class EditorialIssueSchema(BaseModel):
    """One concrete data-quality issue attached to a queue record."""

    code: str
    label: str
    severity: str


class EditorialCompletenessCriterionSchema(BaseModel):
    """One transparent component of the 100-point completeness score."""

    key: str
    label: str
    weight: int = Field(gt=0, le=100)
    completed: bool


class EditorialQueueItemSchema(BaseModel):
    """A person enriched with workflow, quality, and audit metadata."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    person_type: str
    status: PublicationStatus
    avatar: PersonAvatarSchema | None = None
    updated_at: datetime
    last_modified_by: PersonLastEditorSchema | None = None
    age_days: int
    completeness_score: int = Field(ge=0, le=100)
    completeness_criteria: list[EditorialCompletenessCriterionSchema]
    priority: EditorialPriority
    issues: list[EditorialIssueSchema]
    can_publish: bool


class EditorialQueueCountsSchema(BaseModel):
    """Queue counters used by filters and sidebar badges."""

    total: int
    draft: int
    review: int
    urgent: int
    high: int
    normal: int


class EditorialQueueResponseSchema(BaseModel):
    """Paginated editorial queue."""

    items: list[EditorialQueueItemSchema]
    counts: EditorialQueueCountsSchema
    total: int
    page: int
    per_page: int
    pages: int


class EditorialStatusCountSchema(BaseModel):
    """Number of person records in a publication state."""

    status: PublicationStatus
    count: int


class EditorialCompletionBucketSchema(BaseModel):
    """One completeness range in the dashboard distribution."""

    key: str
    label: str
    count: int
    percentage: int


class EditorialMonthlyActivitySchema(BaseModel):
    """Published records grouped by their latest modification month."""

    month: str
    count: int


class EditorialResourceCountsSchema(BaseModel):
    """Real database resource totals displayed in system status."""

    users: int
    countries: int
    orders: int
    bibliography: int


class EditorialDashboardSchema(BaseModel):
    """Complete data contract for the editorial dashboard."""

    generated_at: datetime
    total_persons: int
    status_counts: list[EditorialStatusCountSchema]
    attention_count: int
    unknown_license_images: int
    completion: list[EditorialCompletionBucketSchema]
    monthly_activity: list[EditorialMonthlyActivitySchema]
    recent_records: list[EditorialQueueItemSchema]
    queue_preview: list[EditorialQueueItemSchema]
    queue_counts: EditorialQueueCountsSchema
    resources: EditorialResourceCountsSchema


class EditorialTransitionSchema(BaseModel):
    """Request a controlled publication-status transition."""

    target_status: PublicationStatus
    note: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_target(self) -> EditorialTransitionSchema:
        if self.target_status not in {
            PublicationStatus.DRAFT,
            PublicationStatus.REVIEW,
            PublicationStatus.PUBLISHED,
            PublicationStatus.ARCHIVED,
        }:
            raise ValueError("Nieobsługiwany status docelowy")
        return self


class EditorialTransitionResponseSchema(BaseModel):
    """Result of a successful workflow transition."""

    person_id: uuid.UUID
    previous_status: PublicationStatus
    status: PublicationStatus
    updated_at: datetime
