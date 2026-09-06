"""Protected, person-scoped endpoints for editorial translations."""

from __future__ import annotations

import uuid
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.person_translations import (
    CreatePersonTranslationCommand,
    UpdatePersonTranslationCommand,
)
from src.application.services.person_translation_service import (
    PersonTranslationConflictError,
    PersonTranslationContentError,
    PersonTranslationMutationResult,
    PersonTranslationNotFoundError,
    PersonTranslationService,
    PersonTranslationStateError,
    PersonTranslationVersionConflictError,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.person_translations.schemas import (
    PersonTranslationDeleteSchema,
    PersonTranslationListSchema,
    PersonTranslationMutationSchema,
    PersonTranslationSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()

LANGUAGE_PATH = Path(
    min_length=2,
    max_length=35,
    pattern=r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$",
    description="BCP 47 content locale",
)


def _raise_translation_error(exc: Exception) -> NoReturn:
    if isinstance(exc, PersonTranslationNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, PersonTranslationContentError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "code": "translation_content_empty"},
        ) from exc
    if isinstance(exc, PersonTranslationVersionConflictError):
        code = f"{exc.resource}_version_conflict"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "code": code,
                "expected_version": exc.expected_version,
                "current_version": exc.current_version,
            },
        ) from exc
    if isinstance(exc, PersonTranslationStateError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "code": "translation_parent_not_draft"},
        ) from exc
    if isinstance(exc, PersonTranslationConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "code": "translation_locale_conflict"},
        ) from exc
    raise exc


def _mutation_schema(result: PersonTranslationMutationResult) -> PersonTranslationMutationSchema:
    translation = PersonTranslationSchema.model_validate(result.translation)
    return PersonTranslationMutationSchema(
        **translation.model_dump(),
        person_version=result.person_version,
    )


@router.get(
    "/{person_id}/translations",
    response_model=PersonTranslationListSchema,
    summary="List editorial translations for a person",
)
async def list_person_translations(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("translations", "read")),
) -> PersonTranslationListSchema:
    try:
        result = await PersonTranslationService(db).list_active(person_id)
    except PersonTranslationNotFoundError as exc:
        _raise_translation_error(exc)
    return PersonTranslationListSchema(
        items=[PersonTranslationSchema.model_validate(item) for item in result.items],
        person_version=result.person_version,
        person_status=result.person_status,
    )


@router.post(
    "/{person_id}/translations",
    response_model=PersonTranslationMutationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create or restore a draft person translation",
)
async def create_person_translation(
    person_id: uuid.UUID,
    data: CreatePersonTranslationCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("translations", "create")),
) -> PersonTranslationMutationSchema:
    try:
        result = await PersonTranslationService(db).create(
            person_id,
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except (
        PersonTranslationConflictError,
        PersonTranslationNotFoundError,
        PersonTranslationStateError,
        PersonTranslationVersionConflictError,
    ) as exc:
        _raise_translation_error(exc)
    return _mutation_schema(result)


@router.patch(
    "/{person_id}/translations/{language_code}",
    response_model=PersonTranslationMutationSchema,
    summary="Update a draft person translation",
)
async def update_person_translation(
    person_id: uuid.UUID,
    language_code: Annotated[str, LANGUAGE_PATH],
    data: UpdatePersonTranslationCommand,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("translations", "update")),
) -> PersonTranslationMutationSchema:
    try:
        result = await PersonTranslationService(db).update(
            person_id,
            language_code,
            data,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except (
        PersonTranslationContentError,
        PersonTranslationNotFoundError,
        PersonTranslationStateError,
        PersonTranslationVersionConflictError,
    ) as exc:
        _raise_translation_error(exc)
    return _mutation_schema(result)


@router.delete(
    "/{person_id}/translations/{language_code}",
    response_model=PersonTranslationDeleteSchema,
    summary="Soft-delete a draft person translation",
)
async def delete_person_translation(
    person_id: uuid.UUID,
    language_code: Annotated[str, LANGUAGE_PATH],
    request: Request,
    expected_person_version: Annotated[int, Query(ge=1)],
    expected_version: Annotated[int, Query(ge=1)],
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("translations", "delete")),
) -> PersonTranslationDeleteSchema:
    try:
        result = await PersonTranslationService(db).delete(
            person_id,
            language_code,
            expected_person_version=expected_person_version,
            expected_version=expected_version,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except (
        PersonTranslationNotFoundError,
        PersonTranslationStateError,
        PersonTranslationVersionConflictError,
    ) as exc:
        _raise_translation_error(exc)
    return PersonTranslationDeleteSchema(
        language_code=result.translation.language_code,
        person_version=result.person_version,
    )
