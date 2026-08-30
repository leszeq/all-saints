"""Editorial dashboard aggregation, quality scoring, and review workflow."""

from __future__ import annotations

import re
import unicodedata
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from src.application.services.person_service import PersonService
from src.domain.geography.models import Country, ReligiousOrder
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.identity.models import User
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
    SourceType,
)
from src.presentation.api.v1.editorial.schemas import (
    EditorialCompletenessCriterionSchema,
    EditorialCompletionBucketSchema,
    EditorialDashboardSchema,
    EditorialDuplicateGroupSchema,
    EditorialDuplicatePersonSchema,
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
    EditorialTransitionResponseSchema,
)
from src.presentation.api.v1.persons.schemas import (
    PersonAvatarSchema,
    PersonLastEditorSchema,
    PersonUpdateSchema,
)


class EditorialNotFoundError(ValueError):
    """Raised when a workflow target cannot be found."""


class EditorialTransitionError(ValueError):
    """Raised when a publication transition is not allowed."""


class EditorialAuthorizationError(ValueError):
    """Raised when a workflow transition requires publication permission."""


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    PublicationStatus.DRAFT.value: {PublicationStatus.REVIEW.value},
    PublicationStatus.REVIEW.value: {
        PublicationStatus.DRAFT.value,
        PublicationStatus.PUBLISHED.value,
    },
    PublicationStatus.PUBLISHED.value: {
        PublicationStatus.REVIEW.value,
        PublicationStatus.ARCHIVED.value,
    },
    PublicationStatus.ARCHIVED.value: {PublicationStatus.DRAFT.value},
}

TRANSITION_PERMISSIONS: dict[tuple[str, str], str] = {
    (PublicationStatus.DRAFT.value, PublicationStatus.REVIEW.value): "persons:submit",
    (PublicationStatus.REVIEW.value, PublicationStatus.DRAFT.value): "persons:review",
    (PublicationStatus.REVIEW.value, PublicationStatus.PUBLISHED.value): "persons:review",
    (PublicationStatus.PUBLISHED.value, PublicationStatus.REVIEW.value): "persons:publish",
    (PublicationStatus.PUBLISHED.value, PublicationStatus.ARCHIVED.value): "persons:publish",
    (PublicationStatus.ARCHIVED.value, PublicationStatus.DRAFT.value): "persons:publish",
}


class EditorialService:
    """Read operational metrics and manage publication-state transitions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _has_text(column: InstrumentedAttribute[str | None]) -> ColumnElement[bool]:
        return and_(column.is_not(None), func.length(func.trim(column)) > 0)

    @staticmethod
    def _missing_text(column: InstrumentedAttribute[str | None]) -> ColumnElement[bool]:
        return or_(column.is_(None), func.length(func.trim(column)) == 0)

    @classmethod
    def _quality_expressions(
        cls,
    ) -> tuple[
        ColumnElement[int],
        ColumnElement[int],
        ColumnElement[int],
        ColumnElement[int],
        ColumnElement[int],
    ]:
        source_count = (
            select(func.count(PersonSource.id))
            .where(
                PersonSource.person_id == Person.id,
                PersonSource.deleted_at.is_(None),
                or_(
                    and_(
                        PersonSource.bibliography_id.is_not(None),
                        PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
                    ),
                    and_(
                        PersonSource.historical_source_id.is_not(None),
                        PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
                    ),
                ),
            )
            .correlate(Person)
            .scalar_subquery()
        )
        image_count = (
            select(func.count(Image.id))
            .where(Image.person_id == Person.id, Image.deleted_at.is_(None))
            .correlate(Person)
            .scalar_subquery()
        )
        unknown_license_count = (
            select(func.count(Image.id))
            .where(
                Image.person_id == Person.id,
                Image.deleted_at.is_(None),
                Image.license == ImageLicense.UNKNOWN.value,
            )
            .correlate(Person)
            .scalar_subquery()
        )
        completeness_score = (
            10
            + case((cls._has_text(Person.summary_pl), 15), else_=0)
            + case((cls._has_text(Person.biography_pl), 25), else_=0)
            + case(
                (or_(Person.birth_year.is_not(None), Person.death_year.is_not(None)), 10),
                else_=0,
            )
            + case((Person.state_of_life_id.is_not(None), 10), else_=0)
            + case((source_count > 0, 15), else_=0)
            + case((image_count > 0, 10), else_=0)
            + case((and_(image_count > 0, unknown_license_count == 0), 5), else_=0)
        )
        stale_cutoff = datetime.now(UTC) - timedelta(days=30)
        priority_score = (
            case((Person.status == PublicationStatus.REVIEW.value, 3), else_=0)
            + case((~cls._has_text(Person.biography_pl), 2), else_=0)
            + case((~cls._has_text(Person.summary_pl), 1), else_=0)
            + case((source_count == 0, 2), else_=0)
            + case((image_count == 0, 1), else_=0)
            + case((unknown_license_count > 0, 2), else_=0)
            + case((Person.updated_at < stale_cutoff, 2), else_=0)
        )
        return (
            source_count,
            image_count,
            unknown_license_count,
            completeness_score,
            priority_score,
        )

    @classmethod
    def _person_rows_query(cls) -> Select[tuple[Person, int, int, int, int, int]]:
        source_count, image_count, unknown_count, completeness, priority = (
            cls._quality_expressions()
        )
        return select(
            Person,
            source_count.label("source_count"),
            image_count.label("image_count"),
            unknown_count.label("unknown_license_count"),
            completeness.label("completeness_score"),
            priority.label("priority_score"),
        ).options(selectinload(Person.images))

    @staticmethod
    def _priority(score: int) -> EditorialPriority:
        if score >= 7:
            return EditorialPriority.URGENT
        if score >= 4:
            return EditorialPriority.HIGH
        return EditorialPriority.NORMAL

    @staticmethod
    def _issues(
        person: Person,
        *,
        source_count: int,
        image_count: int,
        unknown_license_count: int,
    ) -> list[EditorialIssueSchema]:
        issues: list[EditorialIssueSchema] = []
        if not person.biography_pl or not person.biography_pl.strip():
            issues.append(
                EditorialIssueSchema(
                    code="missing_biography",
                    label="Brak biogramu",
                    severity="critical",
                )
            )
        if not person.summary_pl or not person.summary_pl.strip():
            issues.append(
                EditorialIssueSchema(
                    code="missing_summary",
                    label="Brak streszczenia",
                    severity="critical",
                )
            )
        if source_count == 0:
            issues.append(
                EditorialIssueSchema(
                    code="missing_sources",
                    label="Brak przypisanych źródeł",
                    severity="warning",
                )
            )
        if image_count == 0:
            issues.append(
                EditorialIssueSchema(
                    code="missing_image",
                    label="Brak obrazu",
                    severity="warning",
                )
            )
        elif unknown_license_count > 0:
            issues.append(
                EditorialIssueSchema(
                    code="unknown_image_license",
                    label="Nieznana licencja obrazu",
                    severity="critical",
                )
            )
        if person.birth_year is None and person.death_year is None:
            issues.append(
                EditorialIssueSchema(
                    code="missing_dates",
                    label="Brak dat życia",
                    severity="warning",
                )
            )
        if person.state_of_life_id is None:
            issues.append(
                EditorialIssueSchema(
                    code="missing_state_of_life",
                    label="Brak stanu życia",
                    severity="warning",
                )
            )
        return issues

    @staticmethod
    def _completeness_criteria(
        person: Person,
        *,
        source_count: int,
        image_count: int,
        unknown_license_count: int,
    ) -> list[EditorialCompletenessCriterionSchema]:
        """Explain every weighted component used by ``_quality_expressions``."""
        return [
            EditorialCompletenessCriterionSchema(
                key="basic_data",
                label="Dane podstawowe",
                weight=10,
                completed=True,
            ),
            EditorialCompletenessCriterionSchema(
                key="summary",
                label="Streszczenie",
                weight=15,
                completed=bool(person.summary_pl and person.summary_pl.strip()),
            ),
            EditorialCompletenessCriterionSchema(
                key="biography",
                label="Biogram",
                weight=25,
                completed=bool(person.biography_pl and person.biography_pl.strip()),
            ),
            EditorialCompletenessCriterionSchema(
                key="life_dates",
                label="Co najmniej jedna data życia",
                weight=10,
                completed=person.birth_year is not None or person.death_year is not None,
            ),
            EditorialCompletenessCriterionSchema(
                key="state_of_life",
                label="Stan życia",
                weight=10,
                completed=person.state_of_life_id is not None,
            ),
            EditorialCompletenessCriterionSchema(
                key="sources",
                label="Przypisane źródło",
                weight=15,
                completed=source_count > 0,
            ),
            EditorialCompletenessCriterionSchema(
                key="image",
                label="Obraz",
                weight=10,
                completed=image_count > 0,
            ),
            EditorialCompletenessCriterionSchema(
                key="image_license",
                label="Zweryfikowana licencja obrazu",
                weight=5,
                completed=image_count > 0 and unknown_license_count == 0,
            ),
        ]

    @classmethod
    def _queue_item(
        cls,
        row: Row[tuple[Person, int, int, int, int, int]],
        editor: User | None,
    ) -> EditorialQueueItemSchema:
        person, source_count, image_count, unknown_count, completeness, priority_score = row
        issues = cls._issues(
            person,
            source_count=source_count,
            image_count=image_count,
            unknown_license_count=unknown_count,
        )
        blockers = {"missing_biography", "missing_summary", "unknown_image_license"}
        now = datetime.now(UTC)
        updated_at = person.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        return EditorialQueueItemSchema(
            id=person.id,
            slug=person.slug,
            canonical_name=person.canonical_name,
            person_type=person.person_type,
            status=person.status,
            version=person.version,
            avatar=(
                PersonAvatarSchema.model_validate(person.avatar)
                if person.avatar is not None
                else None
            ),
            updated_at=person.updated_at,
            last_modified_by=(
                PersonLastEditorSchema.model_validate(editor) if editor is not None else None
            ),
            age_days=max(0, (now - updated_at).days),
            completeness_score=int(completeness),
            completeness_criteria=cls._completeness_criteria(
                person,
                source_count=source_count,
                image_count=image_count,
                unknown_license_count=unknown_count,
            ),
            priority=cls._priority(int(priority_score)),
            issues=issues,
            can_publish=not any(issue.code in blockers for issue in issues),
        )

    @classmethod
    def _quality_record(
        cls,
        row: Row[tuple[Person, int, int, int, int, int]],
    ) -> EditorialQualityRecordSchema:
        person, source_count, image_count, unknown_count, completeness, priority_score = row
        return EditorialQualityRecordSchema(
            id=person.id,
            slug=person.slug,
            canonical_name=person.canonical_name,
            person_type=person.person_type,
            status=person.status,
            avatar=(
                PersonAvatarSchema.model_validate(person.avatar)
                if person.avatar is not None
                else None
            ),
            updated_at=person.updated_at,
            completeness_score=int(completeness),
            source_count=source_count,
            image_count=image_count,
            unknown_license_count=unknown_count,
            priority=cls._priority(int(priority_score)),
            issues=cls._issues(
                person,
                source_count=source_count,
                image_count=image_count,
                unknown_license_count=unknown_count,
            ),
        )

    @staticmethod
    def _normalize_duplicate_key(name: str) -> str:
        polish_letters = str.maketrans({"ł": "l", "Ł": "L"})
        normalized = unicodedata.normalize("NFKD", name.translate(polish_letters))
        without_diacritics = "".join(
            character for character in normalized if not unicodedata.combining(character)
        )
        value = re.sub(r"[^a-zA-Z0-9\s]+", " ", without_diacritics).lower()
        value = re.sub(
            r"\b(sw|swiety|swieta|bl|blogoslawiony|blogoslawiona|czcigodny|czcigodna|sluga|sluzebnica|bozy|boza)\b",
            " ",
            value,
        )
        return " ".join(value.split())

    @classmethod
    def _duplicate_person(
        cls,
        row: Row[tuple[Person, int, int, int, int, int]],
    ) -> EditorialDuplicatePersonSchema:
        person, source_count, image_count, *_ = row
        return EditorialDuplicatePersonSchema(
            id=person.id,
            slug=person.slug,
            canonical_name=person.canonical_name,
            person_type=person.person_type,
            status=person.status,
            birth_year=person.birth_year,
            death_year=person.death_year,
            updated_at=person.updated_at,
            avatar=(
                PersonAvatarSchema.model_validate(person.avatar)
                if person.avatar is not None
                else None
            ),
            source_count=source_count,
            image_count=image_count,
        )

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
        editors = await PersonService(self.db).get_last_editors([person.id for person in persons])
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
            reason = "Ta sama znormalizowana nazwa"
            if len(years) == 1:
                reason += " oraz zgodne lata życia"
            else:
                reason += "; lata życia wymagają porównania"
            groups.append(
                EditorialDuplicateGroupSchema(
                    key=self._normalize_duplicate_key(group[0][0].canonical_name),
                    confidence=confidence,
                    reason=reason,
                    persons=[self._duplicate_person(row) for row in group],
                )
            )

        return groups, len(duplicate_rows), sum(len(group) for group in duplicate_rows)

    async def _source_stats(self) -> EditorialSourceVerificationStatsSchema:
        source_count, *_ = self._quality_expressions()
        active_person_filter = and_(
            Person.deleted_at.is_(None),
            Person.status != PublicationStatus.ARCHIVED.value,
        )
        active_persons = (
            await self.db.execute(select(func.count(Person.id)).where(active_person_filter))
        ).scalar_one()
        undocumented_persons = (
            await self.db.execute(
                select(func.count(Person.id)).where(active_person_filter, source_count == 0)
            )
        ).scalar_one()
        bibliography_sources = (
            await self.db.execute(
                select(func.count(Bibliography.id)).where(Bibliography.deleted_at.is_(None))
            )
        ).scalar_one()
        historical_sources = (
            await self.db.execute(
                select(func.count(HistoricalSource.id)).where(HistoricalSource.deleted_at.is_(None))
            )
        ).scalar_one()
        person_source_links = (
            await self.db.execute(
                select(func.count(PersonSource.id)).where(PersonSource.deleted_at.is_(None))
            )
        ).scalar_one()
        images = (
            await self.db.execute(select(func.count(Image.id)).where(Image.deleted_at.is_(None)))
        ).scalar_one()
        unknown_license_images = (
            await self.db.execute(
                select(func.count(Image.id)).where(
                    Image.deleted_at.is_(None),
                    Image.license == ImageLicense.UNKNOWN.value,
                )
            )
        ).scalar_one()

        return EditorialSourceVerificationStatsSchema(
            bibliography_sources=bibliography_sources,
            historical_sources=historical_sources,
            person_source_links=person_source_links,
            documented_persons=active_persons - undocumented_persons,
            undocumented_persons=undocumented_persons,
            images=images,
            unknown_license_images=unknown_license_images,
        )

    async def _source_verification_count(self) -> int:
        missing_bibliography_reliability = (
            await self.db.execute(
                select(func.count(Bibliography.id)).where(
                    Bibliography.deleted_at.is_(None),
                    Bibliography.reliability_score.is_(None),
                )
            )
        ).scalar_one()
        missing_website_url = (
            await self.db.execute(
                select(func.count(Bibliography.id)).where(
                    Bibliography.deleted_at.is_(None),
                    Bibliography.source_type == SourceType.WEBSITE.value,
                    self._missing_text(Bibliography.url),
                )
            )
        ).scalar_one()
        missing_access_date = (
            await self.db.execute(
                select(func.count(Bibliography.id)).where(
                    Bibliography.deleted_at.is_(None),
                    Bibliography.source_type == SourceType.WEBSITE.value,
                    self._has_text(Bibliography.url),
                    self._missing_text(Bibliography.url_access_date),
                )
            )
        ).scalar_one()
        missing_digitization_url = (
            await self.db.execute(
                select(func.count(HistoricalSource.id)).where(
                    HistoricalSource.deleted_at.is_(None),
                    HistoricalSource.is_digitized.is_(True),
                    self._missing_text(HistoricalSource.digitization_url),
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
        missing_image_source = (
            await self.db.execute(
                select(func.count(Image.id)).where(
                    Image.deleted_at.is_(None),
                    self._missing_text(Image.source_url),
                )
            )
        ).scalar_one()
        orphan_source_links = (
            await self.db.execute(
                select(func.count(PersonSource.id)).where(
                    PersonSource.deleted_at.is_(None),
                    PersonSource.bibliography_id.is_(None),
                    PersonSource.historical_source_id.is_(None),
                )
            )
        ).scalar_one()
        return (
            missing_bibliography_reliability
            + missing_website_url
            + missing_access_date
            + missing_digitization_url
            + unknown_license_images
            + missing_image_source
            + orphan_source_links
        )

    async def _source_verification_items(
        self,
        limit: int = 150,
    ) -> tuple[list[EditorialSourceVerificationItemSchema], int]:
        items: list[EditorialSourceVerificationItemSchema] = []

        def add_item(item: EditorialSourceVerificationItemSchema) -> None:
            items.append(item)

        bibliography_rows = (
            (
                await self.db.execute(
                    select(Bibliography)
                    .where(
                        Bibliography.deleted_at.is_(None),
                        or_(
                            Bibliography.reliability_score.is_(None),
                            and_(
                                Bibliography.source_type == SourceType.WEBSITE.value,
                                self._missing_text(Bibliography.url),
                            ),
                            and_(
                                Bibliography.source_type == SourceType.WEBSITE.value,
                                self._has_text(Bibliography.url),
                                self._missing_text(Bibliography.url_access_date),
                            ),
                        ),
                    )
                    .order_by(Bibliography.updated_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        for source in bibliography_rows:
            if source.reliability_score is None:
                add_item(
                    EditorialSourceVerificationItemSchema(
                        id=source.id,
                        item_type="bibliography",
                        title=source.title,
                        issue="Brak oceny wiarygodności źródła",
                        severity="warning",
                        source_url=source.url,
                        updated_at=source.updated_at,
                    )
                )
            if source.source_type == SourceType.WEBSITE.value and not source.url:
                add_item(
                    EditorialSourceVerificationItemSchema(
                        id=source.id,
                        item_type="bibliography",
                        title=source.title,
                        issue="Źródło internetowe nie ma adresu URL",
                        severity="critical",
                        updated_at=source.updated_at,
                    )
                )
            if (
                source.source_type == SourceType.WEBSITE.value
                and source.url
                and not source.url_access_date
            ):
                add_item(
                    EditorialSourceVerificationItemSchema(
                        id=source.id,
                        item_type="bibliography",
                        title=source.title,
                        issue="Brak daty dostępu do źródła internetowego",
                        severity="warning",
                        source_url=source.url,
                        updated_at=source.updated_at,
                    )
                )

        historical_rows = (
            (
                await self.db.execute(
                    select(HistoricalSource)
                    .where(
                        HistoricalSource.deleted_at.is_(None),
                        HistoricalSource.is_digitized.is_(True),
                        self._missing_text(HistoricalSource.digitization_url),
                    )
                    .order_by(HistoricalSource.updated_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        for historical_source in historical_rows:
            add_item(
                EditorialSourceVerificationItemSchema(
                    id=historical_source.id,
                    item_type="historical_source",
                    title=historical_source.title,
                    issue="Źródło oznaczone jako zdigitalizowane bez linku",
                    severity="warning",
                    updated_at=historical_source.updated_at,
                )
            )

        image_rows = (
            (
                await self.db.execute(
                    select(Image)
                    .where(
                        Image.deleted_at.is_(None),
                        or_(
                            Image.license == ImageLicense.UNKNOWN.value,
                            self._missing_text(Image.source_url),
                        ),
                    )
                    .options(selectinload(Image.person))
                    .order_by(Image.updated_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        for image in image_rows:
            related_person = image.person
            if image.license == ImageLicense.UNKNOWN.value:
                add_item(
                    EditorialSourceVerificationItemSchema(
                        id=image.id,
                        item_type="image",
                        title=image.title or image.url,
                        issue="Nieznana licencja obrazu",
                        severity="critical",
                        related_person_id=related_person.id if related_person else None,
                        related_person_name=(
                            related_person.canonical_name if related_person else None
                        ),
                        source_url=image.source_url,
                        updated_at=image.updated_at,
                    )
                )
            if not image.source_url:
                add_item(
                    EditorialSourceVerificationItemSchema(
                        id=image.id,
                        item_type="image",
                        title=image.title or image.url,
                        issue="Brak adresu źródła obrazu",
                        severity="warning",
                        related_person_id=related_person.id if related_person else None,
                        related_person_name=(
                            related_person.canonical_name if related_person else None
                        ),
                        updated_at=image.updated_at,
                    )
                )

        orphan_rows = (
            await self.db.execute(
                select(PersonSource, Person)
                .join(Person, Person.id == PersonSource.person_id)
                .where(
                    PersonSource.deleted_at.is_(None),
                    PersonSource.bibliography_id.is_(None),
                    PersonSource.historical_source_id.is_(None),
                    Person.deleted_at.is_(None),
                )
                .order_by(PersonSource.updated_at.desc())
                .limit(limit)
            )
        ).all()
        for link, person in orphan_rows:
            add_item(
                EditorialSourceVerificationItemSchema(
                    id=link.id,
                    item_type="person_source",
                    title=f"Przypis źródłowy: {person.canonical_name}",
                    issue="Przypis nie wskazuje na bibliografię ani źródło historyczne",
                    severity="critical",
                    related_person_id=person.id,
                    related_person_name=person.canonical_name,
                    updated_at=link.updated_at,
                )
            )

        items.sort(
            key=lambda item: (
                0 if item.severity == "critical" else 1,
                item.updated_at,
            )
        )
        return items[:limit], await self._source_verification_count()

    async def quality_report(self) -> EditorialQualityReportSchema:
        """Return the complete data quality centre report."""
        problem_records, issue_breakdown, records_with_issues = (
            await self._quality_problem_records()
        )
        duplicate_groups, duplicate_group_count, duplicate_record_count = (
            await self._duplicate_groups()
        )
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
        editors = await PersonService(self.db).get_last_editors([row[0].id for row in rows])
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

    async def transition(
        self,
        person_id: uuid.UUID,
        target_status: PublicationStatus,
        *,
        user_id: uuid.UUID,
        note: str | None = None,
        granted_permissions: set[str] | None = None,
        expected_version: int | None = None,
    ) -> EditorialTransitionResponseSchema:
        """Apply one allowed workflow transition and write a version snapshot."""
        person_service = PersonService(self.db)
        person = await person_service.get_by_id_or_slug(str(person_id))
        if person is None:
            raise EditorialNotFoundError("Rekord nie istnieje")
        previous = str(person.status)
        if target_status.value not in ALLOWED_TRANSITIONS.get(previous, set()):
            raise EditorialTransitionError(
                f"Przejście {previous} → {target_status.value} nie jest dozwolone"
            )
        required_permission = TRANSITION_PERMISSIONS[(previous, target_status.value)]
        if required_permission not in (granted_permissions or set()):
            raise EditorialAuthorizationError(
                f"Ta operacja wymaga uprawnienia {required_permission}"
            )
        normalized_note = note.strip() if note else None
        if (
            previous == PublicationStatus.REVIEW.value
            and target_status == PublicationStatus.DRAFT
            and not normalized_note
        ):
            raise EditorialTransitionError(
                "Zwrócenie rekordu do redaktora wymaga komentarza z uzasadnieniem"
            )
        if target_status == PublicationStatus.PUBLISHED:
            missing = []
            if not person.summary_pl or not person.summary_pl.strip():
                missing.append("streszczenie")
            if not person.biography_pl or not person.biography_pl.strip():
                missing.append("biogram")
            if any(
                image.deleted_at is None and image.license == ImageLicense.UNKNOWN.value
                for image in person.images
            ):
                missing.append("licencja obrazu")
            if missing:
                raise EditorialTransitionError(
                    "Publikacja wymaga uzupełnienia: " + ", ".join(missing)
                )
        summary = normalized_note or f"Workflow redakcyjny: {previous} → {target_status.value}"
        person = await person_service.update_person(
            person,
            PersonUpdateSchema(
                status=target_status,
                change_summary=summary,
                expected_version=expected_version,
            ),
            user_id=user_id,
            allow_status_change=True,
        )
        return EditorialTransitionResponseSchema(
            person_id=person.id,
            previous_status=previous,
            status=person.status,
            updated_at=person.updated_at,
        )
