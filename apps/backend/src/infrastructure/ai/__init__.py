"""
AI infrastructure package.

Provides embedding generation, semantic search and text summarization
with support for multiple providers (OpenAI, Ollama, fallback).
"""

from src.infrastructure.ai.embeddings import EmbeddingService, get_embedding_service
from src.infrastructure.ai.summarizer import SummaryService, get_summary_service

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "SummaryService",
    "get_summary_service",
]
