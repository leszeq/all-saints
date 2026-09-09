"""Editorial dashboard aggregation, quality scoring, and review workflow."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.editorial_models import (
    EditorialCompletionBucketSchema,
    EditorialDashboardSchema,
    EditorialDuplicateGroupSchema,
    EditorialIssueSchema,
    EditorialMonthlyActivitySchema,
    EditorialPriority,
    EditorialQualityIssueBreakdownSchema,
    EditorialQualityRecordSchema,
    EditorialQualityReportSchema,
    EditorialQualitySummarySchema,
    EditorialQueueCountsSchema,
    EditorialQueueItemSchema,
    EditorialQueueResponseSchema,
    EditorialResourceCountsSchema,
    EditorialSourceVerificationItemSchema,
    EditorialSourceVerificationStatsSchema,
    EditorialStatusCountSchema,
)
from src.application.services.editorial_quality import EditorialQualityPolicy
from src.application.services.editorial_source_quality import EditorialSourceQualityReader
from src.application.services.editorial_workflow_service import (
    ALLOWED_TRANSITIONS,
    TRANSITION_PERMISSIONS,
    EditorialAuthorizationError,
    EditorialNotFoundError,
    EditorialTransitionError,
    EditorialWorkflowService,
)
from src.application.services.person_query_service import PersonQueryService
from src.domain.geography.models import Country, ReligiousOrder
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.identity.models import User
from src.domain.sources.models import (
    Bibliography,
    Image,
    ImageLicense,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TRANSITION_PERMISSIONS",
    "EditorialAuthorizationError",
    "EditorialNotFoundError",
    "EditorialService",
    "EditorialTransitionError",
]


class EditorialService(EditorialWorkflowService):
    """Read operational metrics with a legacy-compatible workflow interface."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._source_quality = EditorialSourceQualityReader(db)

    # Compatibility aliases keep existing internal callers stable while the
    # quality policy lives in a focused, independently testable module.
    _has_text = staticmethod(EditorialQualityPolicy.has_text)
    _missing_text = staticmethod(EditorialQualityPolicy.missing_text)
    _quality_expressions = staticmethod(EditorialQualityPolicy.quality_expressions)
    _person_rows_query = staticmethod(EditorialQualityPolicy.person_rows_query)
    _priority = staticmethod(EditorialQualityPolicy.priority)
    _issues = staticmethod(EditorialQualityPolicy.issues)
    _completeness_criteria = staticmethod(EditorialQualityPolicy.completeness_criteria)
    _queue_item = staticmethod(EditorialQualityPolicy.queue_item)
    _quality_record = staticmethod(EditorialQualityPolicy.quality_record)
    _normalize_duplicate_key = staticmethod(EditorialQualityPolicy.normalize_duplicate_key)
    _duplicate_person = staticmethod(EditorialQualityPolicy.duplicate_person)

    async def _queue_counts(self) -> EditorialQueueCountsSchema:
        *_, priority_score = self._quality_expressions()
        queue_filter = and_(
            Person.deleted_at.is_(None),
            Person.status.in_([PublicationStatus.DRAFT.value, PublicationStatus.REVIEW.value]),
        )
        result = await self.db.execute(
            select(
                func.count(Person.id),
                func.count(Person.id).filter(Person.status == PublicationStatus.DRAFT.value),
                func.count(Person.id).filter(Person.status == PublicationStatus.REVIEW.value),
                func.count(Person.id).filter(priority_score >= 4),
                func.count(Person.id).filter(priority_score >= 7),
                func.count(Person.id).filter(and_(priority_score >= 4, priority_score < 7)),
                func.count(Person.id).filter(priority_score < 4),
            ).where(queue_filter)
        )
        total, draft, review, attention, urgent, high, normal = result.one()
        return EditorialQueueCountsSchema(
            total=total,
            draft=draft,
            review=review,
            attention=attention,
            urgent=urgent,
            high=high,
            normal=normal,
        )

    async def list_queue(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        status_filter: PublicationStatus | None = None,
        priority_filter: EditorialPriority | None = None,
        attention_only: bool = False,
    ) -> EditorialQueueResponseSchema:
        """Return paginated draft/review records ordered by computed urgency."""
        *_, priority_score = self._quality_expressions()
        query = self._person_rows_query().where(
            Person.deleted_at.is_(None),
            Person.status.in_([PublicationStatus.DRAFT.value, PublicationStatus.REVIEW.value]),
        )
        if search and search.strip():
            term = search.strip()
            query = query.where(
                or_(
                    Person.canonical_name.ilike(f"%{term}%"),
                    Person.latin_name.ilike(f"%{term}%"),
                )
            )
        if status_filter is not None:
            query = query.where(Person.status == status_filter.value)
        if priority_filter == EditorialPriority.URGENT:
            query = query.where(priority_score >= 7)
        elif priority_filter == EditorialPriority.HIGH:
            query = query.where(and_(priority_score >= 4, priority_score < 7))
        elif priority_filter == EditorialPriority.NORMAL:
            query = query.where(priority_score < 4)
        if attention_only:
            query = query.where(priority_score >= 4)

        count_result = await self.db.execute(
            select(func.count()).select_from(query.order_by(None).subquery())
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            query.order_by(priority_score.desc(), Person.updated_at.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        rows = list(result.unique().all())
        persons = [row[0] for row in rows]
        editors = await PersonQueryService(self.db).get_last_editors(
            [person.id for person in persons]
        )
        return EditorialQueueResponseSchema(
            items=[self._queue_item(row, editors.get(row[0].id)) for row in rows],
            counts=await self._queue_counts(),
            total=total,
            page=page,
            per_page=per_page,
            pages=-(-total // per_page) if total else 1,
        )

    async def _quality_problem_records(
        self,
        limit: int = 150,
    ) -> tuple[
        list[EditorialQualityRecordSchema],
        list[EditorialQualityIssueBreakdownSchema],
        int,
    ]:
        *_, priority_score = self._quality_expressions()
        query = (
            self._person_rows_query()
            .where(
                Person.deleted_at.is_(None),
                Person.status != PublicationStatus.ARCHIVED.value,
            )
            .order_by(priority_score.desc(), Person.updated_at.asc())
        )
        rows = list((await self.db.execute(query)).unique().all())

        issue_counter: Counter[str] = Counter()
        issue_meta: dict[str, EditorialIssueSchema] = {}
        records: list[EditorialQualityRecordSchema] = []
        records_with_issues = 0
        for row in rows:
            record = self._quality_record(row)
            if not record.issues:
                continue
            records_with_issues += 1
            if len(records) < limit:
                records.append(record)
            for issue in record.issues:
                issue_counter[issue.code] += 1
                issue_meta.setdefault(issue.code, issue)

        severity_rank = {"critical": 0, "warning": 1}
        breakdown = [
            EditorialQualityIssueBreakdownSchema(
                code=code,
                label=issue_meta[code].label,
                severity=issue_meta[code].severity,
                count=count,
            )
            for code, count in issue_counter.most_common()
        ]
        breakdown.sort(
            key=lambda issue: (
                severity_rank.get(issue.severity, 9),
                -issue.count,
                issue.label,
            )
        )
        return records, breakdown, records_with_issues

    async def _duplicate_groups(
        self,
        limit: int = 50,
    ) -> tuple[list[EditorialDuplicateGroupSchema], int, int]:
        query = (
            self._person_rows_query()
            .where(
                Person.deleted_at.is_(None),
                Person.status != PublicationStatus.ARCHIVED.value,
            )
            .order_by(Person.canonical_name.asc())
        )
        rows = list((await self.db.execute(query)).unique().all())
        grouped: dict[str, list[Row[tuple[Person, int, int, int, int, int]]]] = {}
        for row in rows:
            person = row[0]
            key = self._normalize_duplicate_key(person.canonical_name)
            if len(key) < 3:
                continue
            grouped.setdefault(key, []).append(row)

        duplicate_rows = [group for group in grouped.values() if len(group) > 1]
        duplicate_rows.sort(
            key=lambda group: (
                -len(group),
                self._normalize_duplicate_key(group[0][0].canonical_name),
            )
        )

        groups: list[EditorialDuplicateGroupSchema] = []
        for group in duplicate_rows[:limit]:
            years = {(row[0].birth_year, row[0].death_year) for row in group}
            confidence = 95 if len(years) == 1 else 85
            reason_code = "same_normalized_name_and_life_years"
            reason = "Ta sama znormalizowana nazwa"
            if len(years) == 1:
                reason += " oraz zgodne lata życia"
            else:
                reason_code = "same_normalized_name_different_life_years"
                reason += "; lata życia wymagają porównania"
            groups.append(
                EditorialDuplicateGroupSchema(
                    key=self._normalize_duplicate_key(group[0][0].canonical_name),
                    confidence=confidence,
                    reason_code=reason_code,
                    reason=reason,
                    persons=[self._duplicate_person(row) for row in group],
                )
            )

        return groups, len(duplicate_rows), sum(len(group) for group in duplicate_rows)

    async def _source_stats(self) -> EditorialSourceVerificationStatsSchema:
        return await self._source_quality.stats()

    async def _source_verification_count(self) -> int:
        return await self._source_quality.verification_count()

    async def _source_verification_items(
        self,
        limit: int = 150,
    ) -> tuple[list[EditorialSourceVerificationItemSchema], int]:
        return await self._source_quality.verification_items(limit)

    async def quality_report(self) -> EditorialQualityReportSchema:
        """Return the complete data quality centre report."""
        (
            problem_records,
            issue_breakdown,
            records_with_issues,
        ) = await self._quality_problem_records()
        (
            duplicate_groups,
            duplicate_group_count,
            duplicate_record_count,
        ) = await self._duplicate_groups()
        source_stats = await self._source_stats()
        source_items, source_item_count = await self._source_verification_items()
        total_issues = sum(issue.count for issue in issue_breakdown)

        return EditorialQualityReportSchema(
            generated_at=datetime.now(UTC),
            summary=EditorialQualitySummarySchema(
                records_with_issues=records_with_issues,
                total_issues=total_issues,
                duplicate_groups=duplicate_group_count,
                duplicate_records=duplicate_record_count,
                source_items_to_review=source_item_count,
                bibliography_sources=source_stats.bibliography_sources,
                historical_sources=source_stats.historical_sources,
                person_source_links=source_stats.person_source_links,
                documented_persons=source_stats.documented_persons,
                undocumented_persons=source_stats.undocumented_persons,
                unknown_license_images=source_stats.unknown_license_images,
            ),
            issue_breakdown=issue_breakdown,
            problem_records=problem_records,
            duplicate_groups=duplicate_groups,
            source_stats=source_stats,
            source_verification_items=source_items,
        )

    async def _recent_records(self, limit: int = 5) -> list[EditorialQueueItemSchema]:
        query = (
            self._person_rows_query()
            .where(Person.deleted_at.is_(None))
            .order_by(Person.updated_at.desc())
            .limit(limit)
        )
        rows = list((await self.db.execute(query)).unique().all())
        editors = await PersonQueryService(self.db).get_last_editors([row[0].id for row in rows])
        return [self._queue_item(row, editors.get(row[0].id)) for row in rows]

    async def _completion_distribution(self) -> list[EditorialCompletionBucketSchema]:
        *_, completeness, _priority = self._quality_expressions()
        bucket = case(
            (completeness >= 85, "complete"),
            (completeness >= 60, "partial"),
            (completeness >= 35, "low"),
            else_="critical",
        ).label("bucket")
        rows = (
            await self.db.execute(
                select(bucket, func.count(Person.id))
                .where(
                    Person.deleted_at.is_(None),
                    Person.status != PublicationStatus.ARCHIVED.value,
                )
                .group_by(bucket)
            )
        ).all()
        counts: dict[str, int] = {str(row[0]): int(row[1]) for row in rows}
        total = sum(counts.values())
        definitions = [
            ("complete", "Pełne", 0),
            ("partial", "Częściowe", 0),
            ("low", "Niskie", 0),
            ("critical", "Brak krytyczny", 0),
        ]
        return [
            EditorialCompletionBucketSchema(
                key=key,
                label=label,
                count=counts.get(key, fallback),
                percentage=round((counts.get(key, fallback) / total) * 100) if total else 0,
            )
            for key, label, fallback in definitions
        ]

    async def _monthly_activity(self) -> list[EditorialMonthlyActivitySchema]:
        now = datetime.now(UTC)
        current_index = now.year * 12 + now.month - 1
        months: list[datetime] = []
        for offset in range(11, -1, -1):
            index = current_index - offset
            months.append(datetime(index // 12, index % 12 + 1, 1, tzinfo=UTC))
        start = months[0]
        rows = (
            await self.db.execute(
                select(
                    func.date_trunc("month", Person.updated_at).label("month"),
                    func.count(Person.id),
                )
                .where(
                    Person.deleted_at.is_(None),
                    Person.status == PublicationStatus.PUBLISHED.value,
                    Person.updated_at >= start,
                )
                .group_by("month")
            )
        ).all()
        counts = {month.strftime("%Y-%m"): count for month, count in rows}
        return [
            EditorialMonthlyActivitySchema(
                month=month.strftime("%Y-%m"),
                count=counts.get(month.strftime("%Y-%m"), 0),
            )
            for month in months
        ]

    async def dashboard(self) -> EditorialDashboardSchema:
        """Aggregate every real metric required by the editorial dashboard."""
        status_rows = (
            await self.db.execute(
                select(Person.status, func.count(Person.id))
                .where(Person.deleted_at.is_(None))
                .group_by(Person.status)
            )
        ).all()
        status_counts_map: dict[str, int] = {str(row[0]): int(row[1]) for row in status_rows}
        total_persons = sum(status_counts_map.values())
        *_, priority_score = self._quality_expressions()
        attention_count = (
            await self.db.execute(
                select(func.count(Person.id)).where(
                    Person.deleted_at.is_(None),
                    Person.status != PublicationStatus.ARCHIVED.value,
                    priority_score >= 4,
                )
            )
        ).scalar_one()
        unknown_license_images = (
            await self.db.execute(
                select(func.count(Image.id)).where(
                    Image.deleted_at.is_(None),
                    Image.license == ImageLicense.UNKNOWN.value,
                )
            )
        ).scalar_one()
        queue = await self.list_queue(page=1, per_page=5)

        resources = EditorialResourceCountsSchema(
            users=(
                await self.db.execute(select(func.count(User.id)).where(User.deleted_at.is_(None)))
            ).scalar_one(),
            countries=(
                await self.db.execute(
                    select(func.count(Country.id)).where(Country.deleted_at.is_(None))
                )
            ).scalar_one(),
            orders=(
                await self.db.execute(
                    select(func.count(ReligiousOrder.id)).where(ReligiousOrder.deleted_at.is_(None))
                )
            ).scalar_one(),
            bibliography=(
                await self.db.execute(
                    select(func.count(Bibliography.id)).where(Bibliography.deleted_at.is_(None))
                )
            ).scalar_one(),
        )
        return EditorialDashboardSchema(
            generated_at=datetime.now(UTC),
            total_persons=total_persons,
            status_counts=[
                EditorialStatusCountSchema(
                    status=status, count=status_counts_map.get(status.value, 0)
                )
                for status in PublicationStatus
            ],
            attention_count=attention_count,
            unknown_license_images=unknown_license_images,
            completion=await self._completion_distribution(),
            monthly_activity=await self._monthly_activity(),
            recent_records=await self._recent_records(),
            queue_preview=queue.items,
            queue_counts=queue.counts,
            resources=resources,
        )
