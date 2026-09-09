"""Composition root for public and editorial person endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.presentation.api.v1.persons.catalogue import get_person, list_persons
from src.presentation.api.v1.persons.catalogue import router as catalogue_router
from src.presentation.api.v1.persons.editorial_reads import (
    get_person_for_admin,
    list_persons_for_admin,
)
from src.presentation.api.v1.persons.editorial_reads import router as editorial_reads_router
from src.presentation.api.v1.persons.mutations import (
    create_person,
    delete_person,
    restore_person,
    update_person,
)
from src.presentation.api.v1.persons.mutations import router as mutations_router
from src.presentation.api.v1.persons.profile_portability import (
    export_person_profile,
    import_person_profile,
    validate_person_profile_import,
)
from src.presentation.api.v1.persons.profile_portability import (
    router as profile_portability_router,
)
from src.presentation.api.v1.persons.schemas import (
    PersonDetailSchema,
    PersonListResponseSchema,
)
from src.presentation.api.v1.persons.versions import get_person_versions
from src.presentation.api.v1.persons.versions import router as versions_router

router = APIRouter()

__all__ = [
    "export_person_profile",
    "create_person",
    "delete_person",
    "get_person",
    "get_person_for_admin",
    "get_person_versions",
    "import_person_profile",
    "list_persons",
    "list_persons_for_admin",
    "restore_person",
    "update_person",
    "validate_person_profile_import",
]

# FastAPI cannot include an empty child path into an empty-prefix router, so the
# collection operations are registered here while their implementations stay in
# the catalogue and mutation adapters.
router.add_api_route(
    "",
    list_persons,
    methods=["GET"],
    response_model=PersonListResponseSchema,
    summary="List persons",
    description="Browse saints, blessed, and candidates with full-text search, multi-criteria filtering, and pagination.",
)
router.include_router(editorial_reads_router)
router.include_router(profile_portability_router)

router.add_api_route(
    "",
    create_person,
    methods=["POST"],
    response_model=PersonDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create person",
    description="Create a new person entry in the hagiographic catalogue.",
    responses={
        201: {"description": "Person created together with the first version snapshot"},
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Missing persons:create permission"},
        409: {"description": "Database constraint conflict"},
        422: {"description": "Payload validation failed"},
    },
)
router.include_router(mutations_router)
router.include_router(versions_router)


# Keep the public catch-all slug route after all static editorial routes.
router.include_router(catalogue_router)
