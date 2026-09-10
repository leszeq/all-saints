"""Taxonomy API composition and backwards-compatible exports."""

from fastapi import APIRouter

from src.presentation.api.v1.taxonomy.editorial import create_category, create_tag
from src.presentation.api.v1.taxonomy.editorial import router as editorial_router
from src.presentation.api.v1.taxonomy.public import (
    list_categories,
    list_occupations,
    list_states_of_life,
    list_tags,
)
from src.presentation.api.v1.taxonomy.public import router as public_router
from src.presentation.api.v1.taxonomy.schemas import (
    CategoryCreateSchema,
    CategorySchema,
    OccupationSchema,
    StateOfLifeSchema,
    TagCreateSchema,
    TagSchema,
)

router = APIRouter()
router.include_router(public_router)
router.include_router(editorial_router)

__all__ = [
    "CategoryCreateSchema",
    "CategorySchema",
    "OccupationSchema",
    "StateOfLifeSchema",
    "TagCreateSchema",
    "TagSchema",
    "create_category",
    "create_tag",
    "list_categories",
    "list_occupations",
    "list_states_of_life",
    "list_tags",
]
