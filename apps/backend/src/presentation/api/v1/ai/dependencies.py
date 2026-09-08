"""Dependency providers shared by AI endpoint modules."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai_service import AIService
from src.infrastructure.db.session import get_db_session


async def get_ai_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AIService:
    """Provide an AIService instance with an injected database session."""
    return AIService(db)
