"""Versioned JSON import, validation, and export endpoints for person profiles."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.person_profile_models import (
    PersonProfileDocument,
    PersonProfileValidationResult,
)
from src.application.services.person_profile_service import (
    PersonProfileImportError,
    PersonProfileService,
)
from src.application.services.person_query_service import PersonQueryService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.persons.schemas import PersonDetailSchema
from src.presentation.audit import audit_context_from_request

router = APIRouter()


@router.get(
    "/admin/{id_or_slug}/export",
    response_model=PersonProfileDocument,
    summary="Export a complete person profile as versioned JSON",
)
async def export_person_profile(
    id_or_slug: str,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("export", "read")),
) -> PersonProfileDocument:
    """Export editorial fields and portable order, calendar, and source relations."""
    person = await PersonQueryService(db).get_by_id_or_slug(id_or_slug)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Osoba nie została znaleziona",
        )
    return await PersonProfileService(db).export_profile(person)


@router.post(
    "/import/validate",
    response_model=PersonProfileValidationResult,
    summary="Validate a person profile JSON document",
)
async def validate_person_profile_import(
    document: PersonProfileDocument,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("import", "create")),
) -> PersonProfileValidationResult:
    """Validate schema, duplicates, and database references without writing data."""
    return await PersonProfileService(db).validate_import(document)


@router.post(
    "/import",
    response_model=PersonDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Import a validated person profile JSON document",
)
async def import_person_profile(
    document: PersonProfileDocument,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("import", "create")),
) -> PersonDetailSchema:
    """Create an imported person as a draft together with supported relations."""
    try:
        person = await PersonProfileService(db).import_profile(
            document,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
        )
    except PersonProfileImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "errors": exc.validation.errors,
                "warnings": exc.validation.warnings,
            },
        ) from exc
    return PersonDetailSchema.model_validate(person)
