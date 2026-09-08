"""Person-to-source assignment endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.audit_service import add_audit_log
from src.application.services.person_snapshot import (
    append_relation_version,
    lock_person_for_snapshot,
    serialize_person_snapshot,
)
from src.domain.identity.models import AuditAction, User
from src.domain.sources.models import (
    Bibliography,
    HistoricalSource,
    PersonSource,
    SourceType,
)
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.sources.schemas import (
    PersonSourceCreateSchema,
    PersonSourceSchema,
    PersonWebSourceCreateSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.get(
    "/person-links/{person_id}",
    response_model=list[PersonSourceSchema],
    summary="List sources assigned to a person",
)
async def list_person_sources(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("sources", "read")),
) -> list[PersonSourceSchema]:
    """Return active bibliography and historical-source assignments."""
    result = await db.execute(
        select(PersonSource)
        .options(
            selectinload(PersonSource.bibliography),
            selectinload(PersonSource.historical_source),
        )
        .where(
            PersonSource.person_id == person_id,
            PersonSource.deleted_at.is_(None),
            or_(
                PersonSource.bibliography.has(Bibliography.deleted_at.is_(None)),
                PersonSource.historical_source.has(HistoricalSource.deleted_at.is_(None)),
            ),
        )
        .order_by(PersonSource.is_primary.desc(), PersonSource.created_at.asc())
    )
    return [PersonSourceSchema.model_validate(link) for link in result.scalars().all()]


@router.post(
    "/person-links/{person_id}",
    response_model=PersonSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a source to a person",
)
async def create_person_source(
    person_id: uuid.UUID,
    data: PersonSourceCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("sources", "create")),
) -> PersonSourceSchema:
    """Create a non-duplicated source assignment used by data-quality scoring."""
    person = await lock_person_for_snapshot(db, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")
    previous_snapshot = await serialize_person_snapshot(db, person)

    source_model = Bibliography if data.bibliography_id is not None else HistoricalSource
    source_id = data.bibliography_id or data.historical_source_id
    source = (
        await db.execute(
            select(source_model).where(
                source_model.id == source_id,
                source_model.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Źródło nie istnieje")

    source_field = (
        PersonSource.bibliography_id
        if data.bibliography_id is not None
        else PersonSource.historical_source_id
    )
    existing = (
        await db.execute(
            select(PersonSource).where(
                PersonSource.person_id == person_id,
                source_field == source_id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="To źródło jest już przypisane do postaci",
        )

    link = PersonSource(person_id=person_id, **data.model_dump())
    db.add(link)
    await db.flush()
    previous_snapshot, current_snapshot = await append_relation_version(
        db,
        person,
        previous_snapshot=previous_snapshot,
        changed_by_id=current_user.id,
        change_summary="Dodanie źródła",
    )
    add_audit_log(
        db,
        context=audit_context_from_request(request, current_user),
        action=AuditAction.UPDATE,
        resource_type="persons",
        resource_id=person.id,
        old_value=previous_snapshot,
        new_value=current_snapshot,
        extra_metadata={"relation": "sources", "operation": "add"},
    )
    await db.flush()

    result = await db.execute(
        select(PersonSource)
        .options(
            selectinload(PersonSource.bibliography),
            selectinload(PersonSource.historical_source),
        )
        .where(PersonSource.id == link.id)
    )
    return PersonSourceSchema.model_validate(result.scalar_one())


@router.post(
    "/person-links/{person_id}/web",
    response_model=PersonSourceSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create and assign a website source to a person",
)
async def create_person_web_source(
    person_id: uuid.UUID,
    data: PersonWebSourceCreateSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("sources", "create")),
) -> PersonSourceSchema:
    """Create or reuse a URL source and attach it in one transaction."""
    person = await lock_person_for_snapshot(db, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")
    previous_snapshot = await serialize_person_snapshot(db, person)

    normalized_url = str(data.url)
    bibliography = (
        await db.execute(
            select(Bibliography).where(
                Bibliography.url == normalized_url,
                Bibliography.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if bibliography is None:
        bibliography = Bibliography(
            source_type=SourceType.WEBSITE,
            title=data.title,
            url=normalized_url,
            authors=data.authors,
            publisher=data.publisher,
            year=data.year,
            language=data.language,
            reliability_score=data.reliability_score,
        )
        db.add(bibliography)
        await db.flush()

    existing = (
        await db.execute(
            select(PersonSource).where(
                PersonSource.person_id == person_id,
                PersonSource.bibliography_id == bibliography.id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ten link jest już przypisany do postaci",
        )

    link = PersonSource(
        person_id=person_id,
        bibliography_id=bibliography.id,
        page_reference=data.page_reference,
        relevance_score=data.relevance_score,
        is_primary=data.is_primary,
        notes=data.notes,
    )
    db.add(link)
    await db.flush()
    previous_snapshot, current_snapshot = await append_relation_version(
        db,
        person,
        previous_snapshot=previous_snapshot,
        changed_by_id=current_user.id,
        change_summary="Dodanie źródła internetowego",
    )
    add_audit_log(
        db,
        context=audit_context_from_request(request, current_user),
        action=AuditAction.UPDATE,
        resource_type="persons",
        resource_id=person.id,
        old_value=previous_snapshot,
        new_value=current_snapshot,
        extra_metadata={"relation": "sources", "operation": "add"},
    )
    await db.flush()

    result = await db.execute(
        select(PersonSource)
        .options(
            selectinload(PersonSource.bibliography),
            selectinload(PersonSource.historical_source),
        )
        .where(PersonSource.id == link.id)
    )
    return PersonSourceSchema.model_validate(result.scalar_one())


@router.delete(
    "/person-links/{person_id}/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Remove a source assignment from a person",
)
async def delete_person_source(
    person_id: uuid.UUID,
    link_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("sources", "delete")),
) -> None:
    """Soft-delete one source assignment without deleting the source itself."""
    person = await lock_person_for_snapshot(db, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Osoba nie istnieje")
    link = (
        await db.execute(
            select(PersonSource).where(
                PersonSource.id == link_id,
                PersonSource.person_id == person_id,
                PersonSource.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Przypisanie źródła nie istnieje",
        )
    previous_snapshot = await serialize_person_snapshot(db, person)
    link.deleted_at = datetime.now(UTC)
    await db.flush()
    previous_snapshot, current_snapshot = await append_relation_version(
        db,
        person,
        previous_snapshot=previous_snapshot,
        changed_by_id=current_user.id,
        change_summary="Usunięcie źródła",
    )
    add_audit_log(
        db,
        context=audit_context_from_request(request, current_user),
        action=AuditAction.UPDATE,
        resource_type="persons",
        resource_id=person.id,
        old_value=previous_snapshot,
        new_value=current_snapshot,
        extra_metadata={"relation": "sources", "operation": "remove"},
    )
    await db.flush()
