"""Editorial completeness, priority, issue, and duplicate-detection policy."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from src.application.editorial_models import (
    EditorialCompletenessCriterionSchema,
    EditorialDuplicatePersonSchema,
    EditorialIssueSchema,
    EditorialPriority,
    EditorialQualityRecordSchema,
    EditorialQueueItemSchema,
)
from src.application.person_models import PersonAvatarSchema, PersonLastEditorSchema
from src.domain.hagiography.models import Person, PublicationStatus
from src.domain.identity.models import User
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    Image,
    ImageLicense,
    PersonSource,
)

PersonQualityRow = Row[tuple[Person, int, int, int, int, int]]


class EditorialQualityPolicy:
    """Build consistent quality metrics and response records for a person."""

    PUBLICATION_BLOCKER_CODES = frozenset(
        {"missing_biography", "missing_summary", "missing_sources", "unknown_image_license"}
    )

    @staticmethod
    def has_text(column: InstrumentedAttribute[str | None]) -> ColumnElement[bool]:
        return and_(column.is_not(None), func.length(func.trim(column)) > 0)

    @staticmethod
    def missing_text(column: InstrumentedAttribute[str | None]) -> ColumnElement[bool]:
        return or_(column.is_(None), func.length(func.trim(column)) == 0)

    @staticmethod
    def source_count_expression() -> ColumnElement[int]:
        """Return the active, non-orphaned source count for a person."""
        return (
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

    @classmethod
    def quality_expressions(
        cls,
    ) -> tuple[
        ColumnElement[int],
        ColumnElement[int],
        ColumnElement[int],
        ColumnElement[int],
        ColumnElement[int],
    ]:
        source_count = cls.source_count_expression()
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
            + case((cls.has_text(Person.summary_pl), 15), else_=0)
            + case((cls.has_text(Person.biography_pl), 25), else_=0)
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
            + case((~cls.has_text(Person.biography_pl), 2), else_=0)
            + case((~cls.has_text(Person.summary_pl), 1), else_=0)
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
    def person_rows_query(cls) -> Select[tuple[Person, int, int, int, int, int]]:
        source_count, image_count, unknown_count, completeness, priority = cls.quality_expressions()
        return select(
            Person,
            source_count.label("source_count"),
            image_count.label("image_count"),
            unknown_count.label("unknown_license_count"),
            completeness.label("completeness_score"),
            priority.label("priority_score"),
        ).options(selectinload(Person.images))

    @staticmethod
    def priority(score: int) -> EditorialPriority:
        if score >= 7:
            return EditorialPriority.URGENT
        if score >= 4:
            return EditorialPriority.HIGH
        return EditorialPriority.NORMAL

    @staticmethod
    def issues(
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
    def completeness_criteria(
        person: Person,
        *,
        source_count: int,
        image_count: int,
        unknown_license_count: int,
    ) -> list[EditorialCompletenessCriterionSchema]:
        """Explain every weighted component used by ``quality_expressions``."""
        return [
            EditorialCompletenessCriterionSchema(
                key="basic_data", label="Dane podstawowe", weight=10, completed=True
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
                key="image", label="Obraz", weight=10, completed=image_count > 0
            ),
            EditorialCompletenessCriterionSchema(
                key="image_license",
                label="Zweryfikowana licencja obrazu",
                weight=5,
                completed=image_count > 0 and unknown_license_count == 0,
            ),
        ]

    @classmethod
    def publication_blockers(
        cls,
        person: Person,
        *,
        source_count: int,
        image_count: int,
        unknown_license_count: int,
    ) -> list[EditorialIssueSchema]:
        """Return the quality issues that must block publication."""
        order = {
            "missing_summary": 0,
            "missing_biography": 1,
            "missing_sources": 2,
            "unknown_image_license": 3,
        }
        blockers = [
            issue
            for issue in cls.issues(
                person,
                source_count=source_count,
                image_count=image_count,
                unknown_license_count=unknown_license_count,
            )
            if issue.code in cls.PUBLICATION_BLOCKER_CODES
        ]
        return sorted(blockers, key=lambda issue: order[issue.code])

    @classmethod
    def queue_item(
        cls,
        row: PersonQualityRow,
        editor: User | None,
    ) -> EditorialQueueItemSchema:
        person, source_count, image_count, unknown_count, completeness, priority_score = row
        issues = cls.issues(
            person,
            source_count=source_count,
            image_count=image_count,
            unknown_license_count=unknown_count,
        )
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
            completeness_criteria=cls.completeness_criteria(
                person,
                source_count=source_count,
                image_count=image_count,
                unknown_license_count=unknown_count,
            ),
            priority=cls.priority(int(priority_score)),
            issues=issues,
            can_publish=not cls.publication_blockers(
                person,
                source_count=source_count,
                image_count=image_count,
                unknown_license_count=unknown_count,
            ),
        )

    @classmethod
    def quality_record(cls, row: PersonQualityRow) -> EditorialQualityRecordSchema:
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
            priority=cls.priority(int(priority_score)),
            issues=cls.issues(
                person,
                source_count=source_count,
                image_count=image_count,
                unknown_license_count=unknown_count,
            ),
        )

    @staticmethod
    def normalize_duplicate_key(name: str) -> str:
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

    @staticmethod
    def duplicate_person(row: PersonQualityRow) -> EditorialDuplicatePersonSchema:
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
