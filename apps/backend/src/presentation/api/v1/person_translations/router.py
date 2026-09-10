"""Person translation API composition and backwards-compatible exports."""

from fastapi import APIRouter

from src.presentation.api.v1.person_translations.errors import (
    LANGUAGE_PATH,
    mutation_schema,
    raise_translation_error,
)
from src.presentation.api.v1.person_translations.mutations import (
    create_person_translation,
    delete_person_translation,
    update_person_translation,
)
from src.presentation.api.v1.person_translations.mutations import router as mutations_router
from src.presentation.api.v1.person_translations.reads import list_person_translations
from src.presentation.api.v1.person_translations.reads import router as reads_router

router = APIRouter()

_mutation_schema = mutation_schema
_raise_translation_error = raise_translation_error

__all__ = [
    "LANGUAGE_PATH",
    "create_person_translation",
    "delete_person_translation",
    "list_person_translations",
    "mutation_schema",
    "raise_translation_error",
    "update_person_translation",
]

router.include_router(reads_router)
router.include_router(mutations_router)
