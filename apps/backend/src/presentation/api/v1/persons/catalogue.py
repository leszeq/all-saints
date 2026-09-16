"""Public, localized person catalogue endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_localization import resolve_person_content
from src.application.services.person_query_service import PersonQueryService
from src.application.services.person_source_service import PersonSourceService
from src.domain.hagiography.models import (
    Era,
    EraPeriod,
    Gender,
    PatronageGroup,
    Person,
    PersonSort,
    PersonType,
)
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.persons.schemas import (
    PersonDetailSchema,
    PersonListItemSchema,
    PersonListResponseSchema,
    PersonLocalizedSummarySchema,
)
from src.presentation.api.v1.sources.public_schemas import PublicPersonSourceSchema

router = APIRouter()

LOCALE_QUERY = Query(
    min_length=2,
    max_length=35,
    pattern=r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$",
    description="Requested BCP 47 content locale; falls back to the primary language and Polish",
)


def _localized_list_item(person: Person, locale: str) -> PersonListItemSchema:
    payload = PersonListItemSchema.model_validate(person)
    content = resolve_person_content(person, locale)
    summary = PersonLocalizedSummarySchema.model_validate(content.model_dump())
    return payload.model_copy(update={"localized_content": summary})


def _localized_detail(person: Person, locale: str) -> PersonDetailSchema:
    payload = PersonDetailSchema.model_validate(person)
    return payload.model_copy(update={"localized_content": resolve_person_content(person, locale)})


async def list_persons(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = Query(None, max_length=200),
    person_type: Annotated[
        list[PersonType] | None, Query(description="One or more Church recognition types")
    ] = None,
    gender: Annotated[list[Gender] | None, Query(description="One or more genders")] = None,
    era: Annotated[list[Era] | None, Query(description="One or more historical eras")] = None,
    period: Annotated[
        list[EraPeriod] | None, Query(description="One or more public timeline groups")
    ] = None,
    patronage: Annotated[
        list[PatronageGroup] | None,
        Query(description="One or more public patronage discovery groups"),
    ] = None,
    country_id: uuid.UUID | None = None,
    is_featured: bool | None = None,
    sort: PersonSort = PersonSort.NAME_ASC,
    locale: Annotated[str, LOCALE_QUERY] = "pl",
    db: AsyncSession = Depends(get_db_session),
) -> PersonListResponseSchema:
    """List published persons with optional filters."""
    items, total = await PersonQueryService(db).list_persons(
        page=page,
        per_page=per_page,
        search=search,
        person_type=person_type,
        gender=gender,
        era=era,
        period=period,
        patronage=patronage,
        country_id=country_id,
        is_featured=is_featured,
        published_only=True,
        sort=sort,
        include_translations=True,
    )

    pages = -(-total // per_page) if total > 0 else 1
    return PersonListResponseSchema(
        items=[_localized_list_item(person, locale) for person in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{id_or_slug}",
    response_model=PersonDetailSchema,
    summary="Get person detail",
    description="Fetch a single person by UUID or URL slug.",
)
async def get_person(
    id_or_slug: str,
    locale: Annotated[str, LOCALE_QUERY] = "pl",
    db: AsyncSession = Depends(get_db_session),
) -> PersonDetailSchema:
    """Fetch a published person with localized content."""
    person = await PersonQueryService(db).get_by_id_or_slug(
        id_or_slug,
        published_only=True,
        include_translations=True,
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )
    links = await PersonSourceService(db).list_sources(person.id)
    payload = _localized_detail(person, locale)
    payload.sources = [PublicPersonSourceSchema.from_link(link) for link in links]
    return payload
