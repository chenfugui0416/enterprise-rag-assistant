"""Real pgvector integration tests.

The suite is intentionally skipped when the configured PostgreSQL endpoint is not
reachable, which keeps CI independent from the developer's SSH tunnel.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import Document, DocumentStatus, KnowledgeBase, User
from app.rag.chunking import chunk_document
from app.rag.embeddings import DocumentIngestionService, EmbeddingService
from app.rag.loaders import load_document
from app.rag.providers.mock import MockEmbeddingProvider


def _database_url() -> str:
    from app.core.config import get_settings

    return get_settings().database_url


@pytest.fixture
async def pg_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(_database_url(), pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"pgvector integration database is unavailable: {type(exc).__name__}")
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def seeded_document(pg_engine: AsyncEngine) -> AsyncIterator[tuple[AsyncSession, Document]]:
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    session = session_factory()
    user = User(
        email=f"m1-04-{uuid4().hex}@example.test",
        password_hash="test-only",
        display_name="M1-04 integration",
    )
    knowledge_base = KnowledgeBase(owner=user, name=f"M1-04 {uuid4().hex}")
    document = Document(
        knowledge_base=knowledge_base,
        filename="guide.txt",
        storage_path="integration-fixture/guide.txt",
        mime_type="text/plain",
        size_bytes=64,
        sha256=uuid4().hex * 2,
    )
    session.add(document)
    await session.commit()
    user_id = user.id
    knowledge_base_id = knowledge_base.id
    document_id = document.id
    try:
        yield session, document
    finally:
        await session.rollback()
        # Use SQL DELETE so PostgreSQL cascades cleanly without SQLAlchemy trying to
        # null the non-nullable owner_id relationship first.
        await session.execute(delete(Document).where(Document.id == document_id))
        await session.execute(delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
        await session.close()


@pytest.mark.integration
async def test_parse_chunk_embed_store_and_reprocess_idempotently(
    seeded_document: tuple[AsyncSession, Document], tmp_path
) -> None:
    session, document = seeded_document
    source = tmp_path / "guide.txt"
    source.write_text("年假制度\n\n员工每年享有带薪年假。\n\n申请需提前提交。", encoding="utf-8")
    parsed = load_document(source)
    chunks = chunk_document(parsed, max_tokens=8)
    service = DocumentIngestionService(
        EmbeddingService(MockEmbeddingProvider(dimension=1024), dimension=1024, batch_size=2)
    )

    first = await service.ingest(session, document.id, parsed, chunking_options={"max_tokens": 8})
    first_count = await session.scalar(
        text("SELECT count(*) FROM document_chunks WHERE document_id = :document_id"),
        {"document_id": document.id},
    )
    assert first.chunk_count == len(chunks)
    assert first.chunk_count > 1
    assert first_count == first.chunk_count
    assert (
        await session.scalar(
            text("SELECT status::text FROM documents WHERE id = :document_id"),
            {"document_id": document.id},
        )
        == DocumentStatus.READY.value
    )

    index_definition = await session.scalar(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = current_schema() "
            "AND indexname = 'ix_document_chunks_embedding_hnsw'"
        )
    )
    assert index_definition is not None
    assert "USING hnsw" in index_definition
    assert "vector_cosine_ops" in index_definition

    query_vector = (await MockEmbeddingProvider(dimension=1024).embed([chunks[0].text]))[0]
    nearest = await session.scalar(
        text(
            "SELECT content FROM document_chunks "
            "WHERE document_id = :document_id AND embedding IS NOT NULL "
            "ORDER BY embedding <=> CAST(:query_vector AS vector) LIMIT 1"
        ),
        {"document_id": document.id, "query_vector": str(query_vector)},
    )
    assert nearest == chunks[0].text

    second = await service.ingest(session, document.id, parsed, chunking_options={"max_tokens": 8})
    second_count = await session.scalar(
        text("SELECT count(*) FROM document_chunks WHERE document_id = :document_id"),
        {"document_id": document.id},
    )
    assert second.chunk_count == first.chunk_count
    assert second_count == first_count
    assert (
        await session.scalar(
            text(
                "SELECT count(DISTINCT chunk_index) "
                "FROM document_chunks WHERE document_id = :document_id"
            ),
            {"document_id": document.id},
        )
        == first_count
    )


@pytest.mark.integration
async def test_failed_embedding_marks_document_failed_without_partial_chunks(
    seeded_document: tuple[AsyncSession, Document], tmp_path
) -> None:
    session, document = seeded_document
    source = tmp_path / "guide.txt"
    source.write_text("失败路径测试。", encoding="utf-8")
    parsed = load_document(source)

    class FailingProvider(MockEmbeddingProvider):
        async def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("provider fixture failure")

    service = DocumentIngestionService(
        EmbeddingService(FailingProvider(dimension=1024), dimension=1024, batch_size=2)
    )
    with pytest.raises(RuntimeError, match="provider fixture failure"):
        await service.ingest(session, document.id, parsed)

    assert (
        await session.scalar(
            text("SELECT status::text FROM documents WHERE id = :document_id"),
            {"document_id": document.id},
        )
        == DocumentStatus.FAILED.value
    )
    assert (
        await session.scalar(
            text("SELECT count(*) FROM document_chunks WHERE document_id = :document_id"),
            {"document_id": document.id},
        )
        == 0
    )
