"""Editorial dashboard aggregation, quality scoring, and review workflow."""

from __future__ import annotations

import uuid
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
)
from src.presentation.api.v1.editorial.schemas import (
    EditorialCompletenessCriterionSchema,
    EditorialCompletionBucketSchema,
    EditorialDashboardSchema,
    EditorialIssueSchema,
    EditorialMonthlyActivitySchema,
    EditorialPriority,
    EditorialQueueCountsSchema,
    EditorialQueueItemSchema,
    EditorialQueueResponseSchema,
    EditorialResourceCountsSchema,
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


class EditorialService:
    """Read operational metrics and manage publication-state transitions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _has_text(column: InstrumentedAttribute[str | None]) -> ColumnElement[bool]:
        return and_(column.is_not(None), func.length(func.trim(column)) > 0)

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
                        PersonSource.historical_source.has(
                            HistoricalSource.deleted_at.is_(None)
                        ),
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

    async def _queue_counts(self) -> EditorialQueueCountsSchema:
        *_, priority_score = self._quality_expressions()
        queue_filter = and_(
            Person.deleted_at.is_(None),
            Person.status.in_(
                [PublicationStatus.DRAFT.value, PublicationStatus.REVIEW.value]
            ),
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
            Person.status.in_(
                [PublicationStatus.DRAFT.value, PublicationStatus.REVIEW.value]
            ),
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
        editors = await PersonService(self.db).get_last_editors(
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
        status_counts_map: dict[str, int] = {
            str(row[0]): int(row[1]) for row in status_rows
        }
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
                await self.db.execute(
                    select(func.count(User.id)).where(User.deleted_at.is_(None))
                )
            ).scalar_one(),
            countries=(
                await self.db.execute(
                    select(func.count(Country.id)).where(Country.deleted_at.is_(None))
                )
            ).scalar_one(),
            orders=(
                await self.db.execute(
                    select(func.count(ReligiousOrder.id)).where(
                        ReligiousOrder.deleted_at.is_(None)
                    )
                )
            ).scalar_one(),
            bibliography=(
                await self.db.execute(
                    select(func.count(Bibliography.id)).where(
                        Bibliography.deleted_at.is_(None)
                    )
                )
            ).scalar_one(),
        )
        return EditorialDashboardSchema(
            generated_at=datetime.now(UTC),
            total_persons=total_persons,
            status_counts=[
                EditorialStatusCountSchema(status=status, count=status_counts_map.get(status.value, 0))
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
        summary = note or f"Workflow redakcyjny: {previous} → {target_status.value}"
        person = await person_service.update_person(
            person,
            PersonUpdateSchema(status=target_status, change_summary=summary),
            user_id=user_id,
        )
        return EditorialTransitionResponseSchema(
            person_id=person.id,
            previous_status=previous,
            status=person.status,
            updated_at=person.updated_at,
        )
