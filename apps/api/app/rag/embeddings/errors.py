"""Errors raised by the embedding and indexing service."""


class EmbeddingError(RuntimeError):
    """The provider returned an invalid or incomplete embedding response."""


class EmbeddingDimensionError(EmbeddingError):
    """An embedding does not match the configured pgvector dimension."""
