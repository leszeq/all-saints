"""Application result and command models for editorial workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from src.application.person_models import PersonAvatarSchema, PersonLastEditorSchema
from src.domain.hagiography.models import PublicationStatus


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
    version: int
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
    attention: int
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


class EditorialQualitySummarySchema(BaseModel):
    """Top-level counters for the data quality centre."""

    records_with_issues: int
    total_issues: int
    duplicate_groups: int
    duplicate_records: int
    source_items_to_review: int
    bibliography_sources: int
    historical_sources: int
    person_source_links: int
    documented_persons: int
    undocumented_persons: int
    unknown_license_images: int


class EditorialQualityIssueBreakdownSchema(BaseModel):
    """Aggregated count for one data-quality issue code."""

    code: str
    label: str
    severity: str
    count: int


class EditorialQualityRecordSchema(BaseModel):
    """One person record with editorial quality metadata."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    person_type: str
    status: PublicationStatus
    avatar: PersonAvatarSchema | None = None
    updated_at: datetime
    completeness_score: int = Field(ge=0, le=100)
    source_count: int
    image_count: int
    unknown_license_count: int
    priority: EditorialPriority
    issues: list[EditorialIssueSchema]


class EditorialDuplicatePersonSchema(BaseModel):
    """One record inside a potential duplicate group."""

    id: uuid.UUID
    slug: str
    canonical_name: str
    person_type: str
    status: PublicationStatus
    birth_year: int | None = None
    death_year: int | None = None
    updated_at: datetime
    avatar: PersonAvatarSchema | None = None
    source_count: int
    image_count: int


class EditorialDuplicateGroupSchema(BaseModel):
    """Potential duplicate group detected from normalized names."""

    key: str
    confidence: int = Field(ge=0, le=100)
    reason_code: str
    reason: str
    persons: list[EditorialDuplicatePersonSchema]


class EditorialSourceVerificationStatsSchema(BaseModel):
    """Real source and citation counts used to explain public statistics."""

    bibliography_sources: int
    historical_sources: int
    person_source_links: int
    documented_persons: int
    undocumented_persons: int
    images: int
    unknown_license_images: int


class EditorialSourceVerificationItemSchema(BaseModel):
    """One source, source assignment, or image requiring editorial verification."""

    id: uuid.UUID
    item_type: str
    title: str
    issue_code: str
    issue: str
    severity: str
    related_person_id: uuid.UUID | None = None
    related_person_name: str | None = None
    source_url: str | None = None
    updated_at: datetime


class EditorialQualityReportSchema(BaseModel):
    """Complete report powering the data quality centre in the admin panel."""

    generated_at: datetime
    summary: EditorialQualitySummarySchema
    issue_breakdown: list[EditorialQualityIssueBreakdownSchema]
    problem_records: list[EditorialQualityRecordSchema]
    duplicate_groups: list[EditorialDuplicateGroupSchema]
    source_stats: EditorialSourceVerificationStatsSchema
    source_verification_items: list[EditorialSourceVerificationItemSchema]


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
    expected_version: int | None = Field(None, ge=1)

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
