"""Shared HTTP error and response mapping for person translations."""

from typing import NoReturn

from fastapi import HTTPException, Path, status

from src.application.services.person_translation_service import (
    PersonTranslationConflictError,
    PersonTranslationContentError,
    PersonTranslationMutationResult,
    PersonTranslationNotFoundError,
    PersonTranslationStateError,
    PersonTranslationVersionConflictError,
)
from src.presentation.api.v1.person_translations.schemas import (
    PersonTranslationMutationSchema,
    PersonTranslationSchema,
)

LANGUAGE_PATH = Path(
    min_length=2,
    max_length=35,
    pattern=r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$",
    description="BCP 47 content locale",
)


def raise_translation_error(exc: Exception) -> NoReturn:
    """Map translation-domain failures to the stable HTTP error contract."""
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


def mutation_schema(
    result: PersonTranslationMutationResult,
) -> PersonTranslationMutationSchema:
    """Serialize a translation mutation together with its parent version."""
    translation = PersonTranslationSchema.model_validate(result.translation)
    return PersonTranslationMutationSchema(
        **translation.model_dump(),
        person_version=result.person_version,
    )
