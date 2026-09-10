"""Protected create endpoints for taxonomy dictionaries."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.taxonomy_service import TaxonomyService
from src.domain.identity.models import User
from src.infrastructure.db.session import get_db_session
from src.presentation.api.v1.auth.router import require_permission
from src.presentation.api.v1.taxonomy.schemas import (
    CategoryCreateSchema,
    CategorySchema,
    TagCreateSchema,
    TagSchema,
)

router = APIRouter()


@router.post(
    "/categories",
    response_model=CategorySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
)
async def create_category(
    data: CategoryCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "create")),
) -> CategorySchema:
    category = await TaxonomyService(db).create_category(data)
    return CategorySchema.model_validate(category)


@router.post(
    "/tags",
    response_model=TagSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
)
async def create_tag(
    data: TagCreateSchema,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("persons", "create")),
) -> TagSchema:
    tag = await TaxonomyService(db).create_tag(data)
    return TagSchema.model_validate(tag)
