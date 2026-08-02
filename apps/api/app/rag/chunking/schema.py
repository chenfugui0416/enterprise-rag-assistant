"""Immutable output and configuration types for document chunking."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Validated limits used by the chunking service."""

    max_tokens: int = 512
    chunk_overlap: int = 0
    min_chunk_tokens: int = 1
    encoding_name: str = "cl100k_base"

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must not be negative.")
        if self.chunk_overlap >= self.max_tokens:
            raise ValueError("chunk_overlap must be smaller than max_tokens.")
        if self.min_chunk_tokens <= 0:
            raise ValueError("min_chunk_tokens must be greater than zero.")
        if self.min_chunk_tokens > self.max_tokens:
            raise ValueError("min_chunk_tokens must not exceed max_tokens.")
        if not self.encoding_name.strip():
            raise ValueError("encoding_name must not be empty.")


@dataclass(frozen=True, slots=True)
class Chunk:
    """A searchable text unit with source metadata for answer citations."""

    index: int
    text: str
    token_count: int
    page_number: int | None = None
    section_title: str | None = None
    source_block_indices: tuple[int, ...] = ()

    @property
    def source_block_range(self) -> tuple[int, int] | None:
        """Return the inclusive source index range represented by this chunk."""

        if not self.source_block_indices:
            return None
        return self.source_block_indices[0], self.source_block_indices[-1]
