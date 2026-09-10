"""Protected read endpoints for editorial person translations."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.person_translation_service import (
    PersonTranslationNotFoundError,
    PersonTranslationService,
)
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.person_translations.errors import raise_translation_error
from src.presentation.api.v1.person_translations.schemas import (
    PersonTranslationListSchema,
    PersonTranslationSchema,
)

router = APIRouter()


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
        raise_translation_error(exc)
    return PersonTranslationListSchema(
        items=[PersonTranslationSchema.model_validate(item) for item in result.items],
        person_version=result.person_version,
        person_status=result.person_status,
    )
