import pytest

from app.rag.embeddings import (
    EmbeddingDimensionError,
    EmbeddingError,
    EmbeddingService,
)
from app.rag.providers.base import ProviderError


class RecordingProvider:
    model_name = "recording"

    def __init__(self, dimension: int = 3) -> None:
        self.dimension = dimension
        self.batches: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return [[float(index)] * self.dimension for index, _ in enumerate(texts)]


class WrongDimensionProvider(RecordingProvider):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return [[0.0] * (self.dimension - 1) for _ in texts]


class ShortResponseProvider(RecordingProvider):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return []


class FailingProvider(RecordingProvider):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise ProviderError("upstream unavailable")


async def test_embedding_batches_preserve_order_and_boundary() -> None:
    provider = RecordingProvider(dimension=3)
    service = EmbeddingService(provider, dimension=3, batch_size=2)

    vectors = await service.embed_texts(["a", "b", "c", "d", "e"])

    assert provider.batches == [["a", "b"], ["c", "d"], ["e"]]
    assert len(vectors) == 5
    assert vectors[0] == [0.0, 0.0, 0.0]
    assert vectors[-1] == [0.0, 0.0, 0.0]


async def test_empty_input_does_not_call_provider() -> None:
    provider = RecordingProvider()
    service = EmbeddingService(provider, dimension=3, batch_size=2)

    assert await service.embed_texts([]) == []
    assert provider.batches == []


async def test_dimension_mismatch_is_rejected_before_write() -> None:
    provider = WrongDimensionProvider(dimension=3)
    service = EmbeddingService(provider, dimension=3, batch_size=2)

    with pytest.raises(EmbeddingDimensionError, match="expected 3, got 2"):
        await service.embed_texts(["a"])


async def test_provider_response_count_mismatch_is_rejected() -> None:
    provider = ShortResponseProvider()
    service = EmbeddingService(provider, dimension=3, batch_size=2)

    with pytest.raises(EmbeddingError, match="returned 0 vectors for 1 texts"):
        await service.embed_texts(["a"])


async def test_provider_error_is_not_swallowed() -> None:
    service = EmbeddingService(FailingProvider(), dimension=3, batch_size=2)

    with pytest.raises(ProviderError, match="upstream unavailable"):
        await service.embed_texts(["a"])


def test_provider_dimension_mismatch_is_rejected_at_service_creation() -> None:
    with pytest.raises(EmbeddingDimensionError, match="expected 3, got 2"):
        EmbeddingService(RecordingProvider(dimension=2), dimension=3, batch_size=2)
