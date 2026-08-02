"""Public response models for the document parsing laboratory."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ParsedBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    kind: Literal["page", "heading", "paragraph", "table", "code", "text"]
    text: str
    page_number: int | None
    section_title: str | None


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    text: str
    token_count: int
    page_number: int | None
    section_title: str | None
    source_block_indices: tuple[int, ...]


class ChunkingConfigResponse(BaseModel):
    max_tokens: int
    chunk_overlap: int


class DocumentPreviewResponse(BaseModel):
    filename: str
    media_type: str
    size_bytes: int
    page_count: int | None
    encoding: str | None
    character_count: int
    block_count: int
    chunk_count: int
    total_tokens: int
    config: ChunkingConfigResponse
    blocks: tuple[ParsedBlockResponse, ...]
    chunks: tuple[ChunkResponse, ...]
