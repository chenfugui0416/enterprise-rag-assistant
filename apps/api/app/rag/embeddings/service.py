"""Batch embedding and document indexing services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import Document, DocumentChunk, DocumentStatus
from app.rag.chunking import Chunk, chunk_document
from app.rag.loaders.schema import ParsedDocument
from app.rag.providers.base import EmbeddingProvider
from app.rag.providers.factory import build_embedding_provider

from .errors import EmbeddingDimensionError, EmbeddingError

_MAX_ERROR_DETAIL = 200


def safe_error_detail(exc: Exception) -> str:
    """把异常压缩成可诊断、但不含正文与凭据的一行。

    SQLAlchemy 的 ``StatementError.__str__`` 会在消息后拼接 ``[SQL: ...]`` 和
    ``[parameters: ...]``，而 parameters 里就是 chunk 正文。实测一次外键违反的
    ``str(exc)`` 长 1241 字符且包含完整正文。按长度截断只是碰运气——SQL 短一点
    正文就落进来了。所以这里改为取 DBAPI 原始异常的首行，结构性地把 SQL 与
    绑定参数排除在外。

    凡是要写入数据库、日志或返回给前端的错误描述，都必须经过这里。
    """

    if isinstance(exc, SQLAlchemyError):
        # exc.orig 是底层 DBAPI 异常，不带 SQLAlchemy 拼接的 SQL/参数段
        origin = getattr(exc, "orig", None)
        raw = str(origin) if origin is not None else exc.__class__.__name__
    else:
        raw = str(exc)

    first_line = raw.strip().splitlines()[0].strip() if raw.strip() else ""
    if not first_line:
        first_line = exc.__class__.__name__
    return f"{type(exc).__name__}: {first_line[:_MAX_ERROR_DETAIL]}"


class EmbeddingService:
    """Turn text into validated vectors in bounded provider requests."""

    def __init__(self, provider: EmbeddingProvider, *, dimension: int, batch_size: int) -> None:
        if dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        if batch_size <= 0:
            raise ValueError("embedding batch size must be positive")
        self.provider = provider
        self.dimension = dimension
        self.batch_size = batch_size

        provider_dimension = getattr(provider, "dimension", dimension)
        if provider_dimension != dimension:
            raise EmbeddingDimensionError(
                f"embedding provider dimension mismatch: expected {dimension}, "
                f"got {provider_dimension}; check EMBEDDING_DIM"
            )

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed all texts while preserving order and validating every response."""

        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            # 直接放行 ProviderError：它已在 provider 层脱敏，这里再包一层只会丢失类型
            batch_vectors = await self.provider.embed(batch)
            if len(batch_vectors) != len(batch):
                raise EmbeddingError(
                    f"embedding provider returned {len(batch_vectors)} vectors for "
                    f"{len(batch)} texts"
                )
            for vector in batch_vectors:
                self._validate_dimension(vector)
            vectors.extend(batch_vectors)
        return vectors

    def _validate_dimension(self, vector: Sequence[float]) -> None:
        if len(vector) != self.dimension:
            raise EmbeddingDimensionError(
                f"embedding dimension mismatch: expected {self.dimension}, got {len(vector)}; "
                "check EMBEDDING_DIM"
            )


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document_id: UUID
    chunk_count: int
    embedding_model: str


class DocumentIngestionService:
    """Index one parsed document with explicit status and transaction boundaries.

    Idempotency uses delete-then-insert inside the final transaction. Chunks are already
    fully embedded before that transaction starts, so a failed provider call leaves the
    previous index intact and a failed database write rolls back the replacement.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service

    async def ingest(
        self,
        session: AsyncSession,
        document_id: UUID,
        parsed_document: ParsedDocument,
        *,
        chunking_options: Mapping[str, Any] | None = None,
    ) -> IngestionResult:
        document = await session.get(Document, document_id)
        if document is None:
            raise ValueError("document not found")

        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        await session.commit()

        try:
            chunks = chunk_document(parsed_document, **(dict(chunking_options or {})))
            vectors = await self.embedding_service.embed_texts([chunk.text for chunk in chunks])
            result = await self._replace_chunks(
                session,
                document_id,
                parsed_document,
                chunks,
                vectors,
            )
        except Exception as exc:
            await session.rollback()
            await self._mark_failed(session, document_id, exc)
            raise
        return result

    async def _replace_chunks(
        self,
        session: AsyncSession,
        document_id: UUID,
        parsed_document: ParsedDocument,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> IngestionResult:
        if len(chunks) != len(vectors):
            raise EmbeddingError("chunk and embedding counts do not match")
        async with session.begin():
            document = await session.get(Document, document_id, with_for_update=True)
            if document is None:
                raise ValueError("document not found")
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            session.add_all(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk.index,
                    content=chunk.text,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    token_count=chunk.token_count,
                    embedding=list(vector),
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            )
            document.page_count = parsed_document.page_count
            document.status = DocumentStatus.READY
            document.error_message = None
        return IngestionResult(
            document_id=document_id,
            chunk_count=len(chunks),
            embedding_model=self.embedding_service.provider.model_name,
        )

    async def _mark_failed(self, session: AsyncSession, document_id: UUID, exc: Exception) -> None:
        try:
            document = await session.get(Document, document_id)
            if document is None:
                return
            document.status = DocumentStatus.FAILED
            # 必须脱敏：该字段会经 API 返回给前端
            document.error_message = safe_error_detail(exc)
            await session.commit()
        except Exception:
            await session.rollback()


def build_embedding_service(settings: Settings | None = None) -> EmbeddingService:
    active_settings = settings or get_settings()
    provider = build_embedding_provider(active_settings)
    return EmbeddingService(
        provider,
        dimension=active_settings.embedding_dim,
        batch_size=active_settings.embedding_batch_size,
    )
