"""Protected CRUD and review endpoints for patronage concepts."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.concept_service import (
    ConceptAssignmentError,
    ConceptConflictError,
    ConceptNotFoundError,
    ConceptService,
)
from src.application.services.published_content_guard import PublishedContentChangeError
from src.domain.hagiography.models import PatronageConcept, PatronageConceptStatus
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.pagination import (
    PAGINATION_RESPONSE_DOCS,
    PageNumber,
    PageSize,
    add_pagination_headers,
)
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.taxonomy.schemas import (
    ConceptAliasCreateSchema,
    ConceptAliasSchema,
    ConceptAssignmentCreateSchema,
    ConceptAssignmentReviewSchema,
    PatronageConceptCreateSchema,
    PatronageConceptManagementSchema,
    PatronageConceptReviewSchema,
    PatronageConceptUpdateSchema,
    PersonPatronageConceptSchema,
)

router = APIRouter()


def _concept_schema(concept: PatronageConcept) -> PatronageConceptManagementSchema:
    return PatronageConceptManagementSchema(
        id=concept.id,
        slug=concept.slug,
        patronage_type=concept.patronage_type,
        name_pl=concept.name_pl,
        name_en=concept.name_en,
        description=concept.description,
        status=concept.status,
        reviewed_by_id=concept.reviewed_by_id,
        reviewed_at=concept.reviewed_at,
        review_note=concept.review_note,
        aliases=[ConceptAliasSchema.model_validate(alias) for alias in concept.aliases],
        assignment_count=len(concept.assignments),
        person_count=len(concept.assignments),
    )


def _raise_service_error(error: ValueError) -> None:
    if isinstance(error, ConceptNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, ConceptConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, ConceptAssignmentError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.get(
    "/patronages/management",
    response_model=list[PatronageConceptManagementSchema],
    responses=PAGINATION_RESPONSE_DOCS,
    summary="List patronage concepts for editorial management",
)
async def list_management_concepts(
    response: Response,
    search: str | None = Query(None, max_length=100),
    concept_status: PatronageConceptStatus | None = Query(None, alias="status"),
    page: PageNumber = 1,
    per_page: PageSize = 100,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("taxonomy", "read")),
) -> list[PatronageConceptManagementSchema]:
    concepts, total = await ConceptService(db).list_concepts(
        search=search,
        status=concept_status,
        page=page,
        per_page=per_page,
    )
    add_pagination_headers(response, total=total, page=page, per_page=per_page)
    return [_concept_schema(concept) for concept in concepts]


@router.post(
    "/patronages",
    response_model=PatronageConceptManagementSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a patronage concept",
)
async def create_management_concept(
    data: PatronageConceptCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("taxonomy", "create")),
) -> PatronageConceptManagementSchema:
    try:
        concept = await ConceptService(db).create_concept(data)
    except ValueError as error:
        _raise_service_error(error)
    return _concept_schema(concept)


@router.patch(
    "/patronages/{concept_id}",
    response_model=PatronageConceptManagementSchema,
    summary="Update a patronage concept",
)
async def update_management_concept(
    concept_id: str,
    data: PatronageConceptUpdateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("taxonomy", "update")),
) -> PatronageConceptManagementSchema:
    try:
        concept = await ConceptService(db).update_concept(concept_id, data)
    except ValueError as error:
        _raise_service_error(error)
    return _concept_schema(concept)


@router.post(
    "/patronages/{concept_id}/aliases",
    response_model=ConceptAliasSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add an alias to a patronage concept",
)
async def create_concept_alias(
    concept_id: str,
    data: ConceptAliasCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("taxonomy", "create")),
) -> ConceptAliasSchema:
    try:
        alias = await ConceptService(db).add_alias(concept_id, data)
    except ValueError as error:
        _raise_service_error(error)
    return ConceptAliasSchema.model_validate(alias)


@router.post(
    "/patronages/{concept_id}/assignments",
    response_model=PersonPatronageConceptSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a person to a patronage concept",
)
async def create_concept_assignment(
    concept_id: str,
    data: ConceptAssignmentCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_permission("taxonomy", "update")),
) -> PersonPatronageConceptSchema:
    try:
        assignment = await ConceptService(db).assign_person(
            concept_id,
            data,
            user_id=user.id,
        )
    except ValueError as error:
        _raise_service_error(error)
    return PersonPatronageConceptSchema.model_validate(assignment)


@router.post(
    "/patronages/{concept_id}/submit",
    response_model=PatronageConceptManagementSchema,
    summary="Submit a patronage concept for review",
)
async def submit_management_concept(
    concept_id: str,
    data: PatronageConceptReviewSchema,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_permission("taxonomy", "submit")),
) -> PatronageConceptManagementSchema:
    if data.target_status != PatronageConceptStatus.REVIEW:
        raise HTTPException(status_code=422, detail="Przekazanie wymaga statusu review")
    try:
        concept = await ConceptService(db).transition_concept(concept_id, data, user_id=user.id)
    except ValueError as error:
        _raise_service_error(error)
    return _concept_schema(concept)


@router.post(
    "/patronages/{concept_id}/review",
    response_model=PatronageConceptManagementSchema,
    summary="Review a patronage concept",
)
async def review_management_concept(
    concept_id: str,
    data: PatronageConceptReviewSchema,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_permission("taxonomy", "review")),
) -> PatronageConceptManagementSchema:
    try:
        concept = await ConceptService(db).transition_concept(concept_id, data, user_id=user.id)
    except ValueError as error:
        _raise_service_error(error)
    return _concept_schema(concept)


@router.post(
    "/patronages/{concept_id}/assignments/{person_id}/review",
    response_model=PersonPatronageConceptSchema,
    summary="Review a person-to-concept assignment",
)
async def review_concept_assignment(
    concept_id: str,
    person_id: uuid.UUID,
    data: ConceptAssignmentReviewSchema,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_permission("taxonomy", "review")),
) -> PersonPatronageConceptSchema:
    try:
        assignment = await ConceptService(db).transition_assignment(
            concept_id,
            person_id,
            data,
            user_id=user.id,
            allow_published_update=user.has_permission("persons", "publish"),
        )
    except PublishedContentChangeError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except ValueError as error:
        _raise_service_error(error)
    return PersonPatronageConceptSchema.model_validate(assignment)
