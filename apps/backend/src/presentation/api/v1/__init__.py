"""
API v1 router – aggregates all v1 endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from src.presentation.api.v1.auth.router import router as auth_router
from src.presentation.api.v1.persons.router import router as persons_router
from src.presentation.api.v1.users.router import router as users_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(persons_router, prefix="/persons", tags=["persons"])
router.include_router(users_router, prefix="/users", tags=["users"])

