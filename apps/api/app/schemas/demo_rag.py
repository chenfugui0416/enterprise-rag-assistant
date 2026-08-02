"""API contracts for the local RAG demonstration workflow."""

from uuid import UUID

from pydantic import BaseModel, Field


class IndexResponse(BaseModel):
    document_id: UUID
    filename: str
    status: str
    chunk_count: int
    embedding_model: str
    duplicate: bool = False


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)


class CitationResponse(BaseModel):
    document_id: UUID
    document_name: str
    chunk_index: int
    score: float
    page_number: int | None
    section_title: str | None
    content: str


class RetrievedResponse(CitationResponse):
    pass


class QueryResponse(BaseModel):
    question: str
    answer: str
    refused: bool
    model_name: str
    citations: tuple[CitationResponse, ...]
    retrieved: tuple[RetrievedResponse, ...]
