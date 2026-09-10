"""Protected mutation endpoints for editorial person translations."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.commands.person_translations import (
    CreatePersonTranslationCommand,
    UpdatePersonTranslationCommand,
)
from src.application.services.person_translation_service import (
    PersonTranslationConflictError,
    PersonTranslationContentError,
    PersonTranslationNotFoundError,
    PersonTranslationService,
    PersonTranslationStateError,
    PersonTranslationVersionConflictError,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.person_translations.errors import (
    LANGUAGE_PATH,
    mutation_schema,
    raise_translation_error,
)
from src.presentation.api.v1.person_translations.schemas import (
    PersonTranslationDeleteSchema,
    PersonTranslationMutationSchema,
)
from src.presentation.audit import audit_context_from_request

router = APIRouter()


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
        raise_translation_error(exc)
    return mutation_schema(result)


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
        raise_translation_error(exc)
    return mutation_schema(result)


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
        raise_translation_error(exc)
    return PersonTranslationDeleteSchema(
        language_code=result.translation.language_code,
        person_version=result.person_version,
    )
