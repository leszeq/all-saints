"""
API v1 router – aggregates all v1 endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.presentation.api.v1.auth.router import router as auth_router
from src.presentation.api.v1.geography.router import router as geography_router
from src.presentation.api.v1.orders.router import router as orders_router
from src.presentation.api.v1.persons.router import router as persons_router
from src.presentation.api.v1.popes.router import router as popes_router
from src.presentation.api.v1.sources.router import router as sources_router
from src.presentation.api.v1.taxonomy.router import router as taxonomy_router
from src.presentation.api.v1.users.router import router as users_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(persons_router, prefix="/persons", tags=["persons"])
router.include_router(geography_router, prefix="/geography", tags=["geography"])
router.include_router(orders_router, prefix="/orders", tags=["orders"])
router.include_router(popes_router, prefix="/popes", tags=["popes"])
router.include_router(sources_router, prefix="/sources", tags=["sources"])
router.include_router(taxonomy_router, prefix="/taxonomy", tags=["taxonomy"])
router.include_router(users_router, prefix="/users", tags=["users"])
