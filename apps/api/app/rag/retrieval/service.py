"""pgvector cosine Top-K retrieval with source metadata for citations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk, DocumentStatus
from app.rag.embeddings import EmbeddingService


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One retrieved chunk and the metadata needed to cite it."""

    chunk_id: UUID
    document_id: UUID
    document_name: str
    chunk_index: int
    content: str
    score: float
    page_number: int | None
    section_title: str | None

    @property
    def citation_label(self) -> str:
        location = []
        if self.page_number is not None:
            location.append(f"第 {self.page_number} 页")
        if self.section_title:
            location.append(self.section_title)
        location_text = " · ".join(location)
        return f"{self.document_name} · Chunk {self.chunk_index}" + (
            f" · {location_text}" if location_text else ""
        )


class VectorSearchService:
    """Embed a query and search chunks inside one knowledge-base boundary."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    async def search(
        self,
        session: AsyncSession,
        knowledge_base_id: UUID,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> tuple[SearchResult, ...]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0 and 1")

        (query_vector,) = await self.embedding_service.embed_texts([normalized_query])
        distance = DocumentChunk.embedding.cosine_distance(query_vector)
        # \u76f8\u4f3c\u5ea6 = 1 - \u4f59\u5f26\u8ddd\u79bb
        # \u9608\u503c\u4e0b\u63a8\u5230 SQL\uff1a\u5148 LIMIT \u518d\u5728
        # Python \u8fc7\u6ee4\uff0c\u4f4e\u5206\u4f1a\u5360\u6389\u540d\u989d\uff0c
        # \u628a\u9ad8\u5206\u7ed3\u679c\u6324\u51fa Top-K
        max_distance = 1.0 - min_score
        statement: Select[tuple[DocumentChunk, str, float]] = (
            select(DocumentChunk, Document.filename, distance.label("distance"))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.knowledge_base_id == knowledge_base_id,
                # 只检索已就绪文档
                # processing/failed 可能残留旧切片
                Document.status == DocumentStatus.READY,
                DocumentChunk.embedding.is_not(None),
                distance <= max_distance,
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await session.execute(statement)).all()
        return tuple(
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_name=document_name,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                # 距离范围 [0,2]，夹到 [0,1]
                score=max(0.0, min(1.0, 1.0 - float(raw_distance))),
                page_number=chunk.page_number,
                section_title=chunk.section_title,
            )
            for chunk, document_name, raw_distance in rows
        )
