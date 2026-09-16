"""Versioned JSON import, validation, and export endpoints for person profiles."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.person_profile_models import (
    PersonProfileDocument,
    PersonProfileValidationResult,
)
from src.application.services.person_profile_export_service import (
    PersonProfileExportService,
)
from src.application.services.person_profile_import_validator import (
    PersonProfileImportValidator,
)
from src.application.services.person_profile_service import (
    PersonProfileImportError,
    PersonProfileService,
)
from src.application.services.person_query_service import PersonQueryService
from src.application.services.person_service import PersonVersionConflictError
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
    return await PersonProfileExportService(db).export_profile(person)


@router.post(
    "/import/validate",
    response_model=PersonProfileValidationResult,
    summary="Validate a person profile JSON document",
)
async def validate_person_profile_import(
    document: PersonProfileDocument,
    overwrite_person_id: uuid.UUID | None = Query(None),
    expected_version: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("import", "create")),
) -> PersonProfileValidationResult:
    """Validate schema, duplicates, and database references without writing data."""
    if overwrite_person_id is not None and not _user.has_permission("persons", "update"):
        raise HTTPException(status_code=403, detail="Nadpisanie profilu wymaga persons:update")
    result = await PersonProfileImportValidator(db).validate_import(
        document,
        overwrite_person_id=overwrite_person_id,
        expected_version=expected_version,
    )
    if (
        overwrite_person_id is not None
        and result.existing_person is not None
        and result.existing_person.status == "published"
        and not _user.has_permission("persons", "publish")
    ):
        raise HTTPException(
            status_code=403, detail="Nadpisanie opublikowanego profilu wymaga persons:publish"
        )
    return result


@router.post(
    "/import",
    response_model=PersonDetailSchema,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": PersonDetailSchema, "description": "Existing profile overwritten"}},
    summary="Import a validated person profile JSON document",
)
async def import_person_profile(
    document: PersonProfileDocument,
    request: Request,
    response: Response,
    overwrite_person_id: uuid.UUID | None = Query(None),
    expected_version: int | None = Query(None, ge=1),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("import", "create")),
) -> PersonDetailSchema:
    """Create a draft or explicitly overwrite a versioned existing profile."""
    try:
        person = await PersonProfileService(db).import_profile(
            document,
            user_id=current_user.id,
            audit_context=audit_context_from_request(request, current_user),
            overwrite_person_id=overwrite_person_id,
            expected_version=expected_version,
            granted_permissions=current_user.get_permissions(),
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
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except PersonVersionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if overwrite_person_id is not None:
        response.status_code = status.HTTP_200_OK
    return PersonDetailSchema.model_validate(person)
