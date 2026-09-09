"""Dependency providers shared by AI endpoint modules."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ai_service import AIService
from src.application.services.ai_summary_service import AISummaryService
from src.application.services.ai_vector_service import AIVectorService
from src.infrastructure.db.session import get_db_session


async def get_ai_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AIService:
    """Provide an AIService instance with an injected database session."""
    return AIService(db)


async def get_ai_vector_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AIVectorService:
    """Provide the focused vector-search service without summary dependencies."""
    return AIVectorService(db)


async def get_ai_summary_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AISummaryService:
    """Provide the focused summary and tagging generation service."""
    return AISummaryService(db)
