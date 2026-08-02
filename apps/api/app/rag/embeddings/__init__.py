"""Embedding and document indexing public API."""

from app.rag.embeddings.errors import EmbeddingDimensionError, EmbeddingError
from app.rag.embeddings.service import (
    DocumentIngestionService,
    EmbeddingService,
    IngestionResult,
    build_embedding_service,
)

__all__ = [
    "DocumentIngestionService",
    "EmbeddingDimensionError",
    "EmbeddingError",
    "EmbeddingService",
    "IngestionResult",
    "build_embedding_service",
]
