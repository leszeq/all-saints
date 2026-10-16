"""Read-only person catalogue, search, and editorial metadata queries."""

from __future__ import annotations

import base64
import binascii
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.hagiography.models import (
    Era,
    EraPeriod,
    Gender,
    Patronage,
    PatronageGroup,
    Person,
    PersonName,
    PersonOrder,
    PersonSlugRedirect,
    PersonSort,
    PersonTranslation,
    PersonType,
    PersonVersion,
    PublicationStatus,
)
from src.domain.hagiography.person_names import normalize_person_name
from src.domain.identity.models import User


@dataclass(frozen=True, slots=True)
class PublicIndexItem:
    """Minimal public record used by crawlers and sitemap generation."""

    id: uuid.UUID
    slug: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PublicIndexPage:
    """Cursor page for published public profile URLs."""

    items: list[PublicIndexItem]
    next_cursor: str | None


class PublicIndexCursorError(ValueError):
    """Raised when a public-index cursor is malformed."""


def _encode_public_index_cursor(updated_at: datetime, person_id: uuid.UUID) -> str:
    timestamp = updated_at.astimezone(UTC).isoformat()
    payload = f"{timestamp}|{person_id}".encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_public_index_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padding = "=" * (-len(cursor) % 4)
        timestamp, raw_person_id = (
            base64.urlsafe_b64decode(f"{cursor}{padding}").decode().split("|", maxsplit=1)
        )
        parsed_timestamp = datetime.fromisoformat(timestamp)
        if parsed_timestamp.tzinfo is None:
            parsed_timestamp = parsed_timestamp.replace(tzinfo=UTC)
        return parsed_timestamp, uuid.UUID(raw_person_id)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise PublicIndexCursorError("Nieprawidłowy kursor indeksu publicznego") from exc


ERA_PERIOD_ERAS: dict[EraPeriod, tuple[Era, ...]] = {
    EraPeriod.EARLY_WITNESSES: (
        Era.APOSTOLIC,
        Era.EARLY_CHURCH,
        Era.LATE_ANTIQUITY,
    ),
    EraPeriod.MEDIEVAL: (Era.MEDIEVAL,),
    EraPeriod.RENEWAL: (Era.EARLY_MODERN,),
    EraPeriod.MODERN: (Era.MODERN, Era.CONTEMPORARY),
}

PATRONAGE_GROUP_TYPES: dict[PatronageGroup, tuple[str, ...]] = {
    PatronageGroup.HEALTH: ("illness", "healthcare"),
    PatronageGroup.FAMILY: ("family",),
    PatronageGroup.WORK: ("profession", "work"),
    PatronageGroup.TRAVEL: ("travel",),
}


def _enum_values(
    value: object | list[object] | tuple[object, ...] | set[object] | None,
) -> list[str]:
    """Normalize a single enum/query value or a multi-select value list."""
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        raw_values = value
    else:
        raw_values = (value,)
    return [
        item.value if hasattr(item, "value") else str(item)
        for item in raw_values
        if item is not None
    ]


class PersonQueryService:
    """Serve person reads without exposing mutation responsibilities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id_or_slug(
        self,
        identifier: str,
        *,
        published_only: bool = False,
        include_translations: bool = False,
    ) -> Person | None:
        """Fetch a person by UUID or slug, optionally limiting access to public records."""
        load_options = [
            selectinload(Person.images),
            selectinload(Person.aliases),
            selectinload(Person.state_of_life),
            selectinload(Person.patronages),
            selectinload(Person.orders).selectinload(PersonOrder.order),
            selectinload(Person.beatification),
            selectinload(Person.canonization),
        ]
        if include_translations:
            load_options.append(selectinload(Person.translations))
        statement = (
            select(Person)
            .options(*load_options)
            .execution_options(populate_existing=True)
            .where(Person.deleted_at.is_(None))
        )
        if published_only:
            statement = statement.where(Person.status == PublicationStatus.PUBLISHED.value)
        try:
            person_id = uuid.UUID(identifier)
            statement = statement.where(Person.id == person_id)
        except ValueError:
            statement = statement.where(Person.slug == identifier)

        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_public_slug_redirect(self, old_slug: str) -> Person | None:
        """Resolve a historical slug only when its target is still public."""
        result = await self.db.execute(
            select(Person)
            .join(PersonSlugRedirect, PersonSlugRedirect.person_id == Person.id)
            .where(
                PersonSlugRedirect.old_slug == old_slug,
                Person.status == PublicationStatus.PUBLISHED.value,
                Person.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_public_index(
        self,
        *,
        cursor: str | None = None,
        limit: int = 100,
    ) -> PublicIndexPage:
        """Return lightweight published profile URLs in stable cursor order."""
        if not 1 <= limit <= 500:
            raise ValueError("Limit indeksu publicznego musi mieścić się w zakresie 1–500")

        query = select(Person.id, Person.slug, Person.updated_at).where(
            Person.status == PublicationStatus.PUBLISHED.value,
            Person.deleted_at.is_(None),
        )
        if cursor:
            updated_at, person_id = _decode_public_index_cursor(cursor)
            query = query.where(
                or_(
                    Person.updated_at < updated_at,
                    and_(Person.updated_at == updated_at, Person.id < person_id),
                )
            )
        query = query.order_by(Person.updated_at.desc(), Person.id.desc()).limit(limit + 1)
        rows = list((await self.db.execute(query)).all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [
            PublicIndexItem(id=person_id, slug=slug, updated_at=updated_at)
            for person_id, slug, updated_at in rows
        ]
        next_cursor = (
            _encode_public_index_cursor(items[-1].updated_at, items[-1].id) if has_more else None
        )
        return PublicIndexPage(items=items, next_cursor=next_cursor)

    async def list_persons(
        self,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        person_type: PersonType | list[PersonType] | None = None,
        status: PublicationStatus | None = None,
        gender: Gender | list[Gender] | None = None,
        era: Era | list[Era] | None = None,
        period: EraPeriod | list[EraPeriod] | None = None,
        patronage: PatronageGroup | list[PatronageGroup] | None = None,
        country_id: uuid.UUID | None = None,
        is_featured: bool | None = None,
        published_only: bool = False,
        sort: PersonSort = PersonSort.NAME_ASC,
        include_translations: bool = False,
    ) -> tuple[list[Person], int]:
        """List persons with full-text search, filtering, and pagination."""
        load_options = [selectinload(Person.images), selectinload(Person.patronages)]
        if include_translations:
            load_options.append(selectinload(Person.translations))
        query = select(Person).options(*load_options).where(Person.deleted_at.is_(None))

        if published_only:
            query = query.where(Person.status == PublicationStatus.PUBLISHED.value)

        person_type_values = _enum_values(person_type)
        if person_type_values:
            query = query.where(Person.person_type.in_(person_type_values))
        if status and not published_only:
            query = query.where(Person.status == status.value)
        gender_values = _enum_values(gender)
        if gender_values:
            query = query.where(Person.gender.in_(gender_values))
        period_values = _enum_values(period)
        era_values = _enum_values(era)
        if period_values:
            period_eras: set[str] = set()
            for period_value in period_values:
                period_eras.update(era.value for era in ERA_PERIOD_ERAS[EraPeriod(period_value)])
            query = query.where(Person.era.in_(sorted(period_eras)))
        elif era_values:
            query = query.where(Person.era.in_(era_values))
        patronage_values = _enum_values(patronage)
        if patronage_values:
            patronage_types: set[str] = set()
            for patronage_value in patronage_values:
                patronage_types.update(PATRONAGE_GROUP_TYPES[PatronageGroup(patronage_value)])
            query = query.where(
                Person.patronages.any(
                    and_(
                        Patronage.deleted_at.is_(None),
                        Patronage.patronage_type.in_(sorted(patronage_types)),
                    )
                )
            )
        if country_id:
            query = query.where(
                or_(Person.birth_country_id == country_id, Person.death_country_id == country_id)
            )
        if is_featured is not None:
            query = query.where(Person.is_featured == is_featured)

        search_score = None
        if search and search.strip():
            term = search.strip()
            like_term = f"%{term}%"
            normalized_term = normalize_person_name(term)
            text_query = func.websearch_to_tsquery("simple", func.unaccent(term))
            full_text_rank = func.coalesce(
                func.ts_rank_cd(Person.search_vector, text_query),
                0.0,
            )
            translation_full_text_rank = (
                select(func.max(func.ts_rank_cd(PersonTranslation.search_vector, text_query)))
                .where(
                    PersonTranslation.person_id == Person.id,
                    PersonTranslation.deleted_at.is_(None),
                    PersonTranslation.search_vector.op("@@")(text_query),
                )
                .correlate(Person)
                .scalar_subquery()
            )
            alias_similarity = (
                select(func.max(func.similarity(PersonName.value, term)))
                .where(
                    PersonName.person_id == Person.id,
                    PersonName.deleted_at.is_(None),
                )
                .correlate(Person)
                .scalar_subquery()
            )
            translation_similarity = (
                select(
                    func.max(
                        func.similarity(
                            func.coalesce(PersonTranslation.canonical_name, ""),
                            term,
                        )
                    )
                )
                .where(
                    PersonTranslation.person_id == Person.id,
                    PersonTranslation.deleted_at.is_(None),
                )
                .correlate(Person)
                .scalar_subquery()
            )
            fuzzy_rank = func.greatest(
                func.similarity(Person.canonical_name, term),
                func.similarity(func.coalesce(Person.canonical_name_en, ""), term),
                func.similarity(func.coalesce(Person.latin_name, ""), term),
                func.coalesce(alias_similarity, 0.0),
                func.coalesce(translation_similarity, 0.0),
            )
            search_score = func.greatest(
                full_text_rank,
                func.coalesce(translation_full_text_rank, 0.0),
            ) + (fuzzy_rank * 0.25)
            query = query.where(
                or_(
                    Person.search_vector.op("@@")(text_query),
                    Person.canonical_name.ilike(like_term),
                    Person.canonical_name_en.ilike(like_term),
                    Person.latin_name.ilike(like_term),
                    Person.canonical_name.op("%")(term),
                    Person.canonical_name_en.op("%")(term),
                    Person.latin_name.op("%")(term),
                    Person.aliases.any(
                        and_(
                            PersonName.deleted_at.is_(None),
                            or_(
                                PersonName.normalized_value == normalized_term,
                                PersonName.value.ilike(like_term),
                                PersonName.value.op("%")(term),
                            ),
                        )
                    ),
                    Person.translations.any(
                        and_(
                            PersonTranslation.deleted_at.is_(None),
                            or_(
                                PersonTranslation.search_vector.op("@@")(text_query),
                                PersonTranslation.canonical_name.ilike(like_term),
                                PersonTranslation.canonical_name.op("%")(term),
                            ),
                        )
                    ),
                    Person.patronages.any(
                        and_(
                            Patronage.deleted_at.is_(None),
                            or_(
                                Patronage.name_pl.ilike(like_term),
                                Patronage.name_en.ilike(like_term),
                                Patronage.description.ilike(like_term),
                                Patronage.patronage_type.ilike(like_term),
                            ),
                        )
                    ),
                )
            )

        count_statement = select(func.count()).select_from(query.subquery())
        total = int((await self.db.execute(count_statement)).scalar_one())

        if search_score is not None:
            query = query.order_by(search_score.desc(), Person.canonical_name.asc())
        elif sort == PersonSort.UPDATED_DESC:
            query = query.order_by(Person.updated_at.desc(), Person.canonical_name.asc())
        else:
            query = query.order_by(Person.canonical_name.asc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_last_editors(
        self,
        person_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, User]:
        """Return the user responsible for the latest version of each person."""
        if not person_ids:
            return {}

        ranked_versions = (
            select(
                PersonVersion.person_id.label("person_id"),
                PersonVersion.changed_by_id.label("changed_by_id"),
                func.row_number()
                .over(
                    partition_by=PersonVersion.person_id,
                    order_by=PersonVersion.version_number.desc(),
                )
                .label("position"),
            )
            .where(PersonVersion.person_id.in_(person_ids))
            .subquery()
        )
        result = await self.db.execute(
            select(ranked_versions.c.person_id, User)
            .join(User, User.id == ranked_versions.c.changed_by_id)
            .where(ranked_versions.c.position == 1)
        )
        rows = cast(Sequence[tuple[uuid.UUID, User]], result.all())
        return dict(rows)

    async def get_person_versions(self, person_id: uuid.UUID) -> list[PersonVersion]:
        """Fetch version history for a person."""
        statement = (
            select(PersonVersion)
            .where(PersonVersion.person_id == person_id)
            .order_by(PersonVersion.version_number.desc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())
