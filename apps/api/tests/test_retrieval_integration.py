"""M1-05 检索的真实 pgvector 集成测试。

设计要点：查询向量由 stub provider 精确给定，而不是让 mock provider 生成哈希向量。
mock embedding 是语义无关的确定性哈希，用它断言"问年假就该返回年假文档"是自欺欺人；
这里要验证的是检索机制本身——余弦排序、Top-K 截断、状态过滤、阈值下推和 HNSW 索引，
这些都与模型语义能力无关，因此可以离线确定性地断言。

数据库不可达时整组跳过，保证 CI 不依赖开发机的 SSH 隧道。
"""

from __future__ import annotations

import math
from collections.abc import AsyncIterator, Sequence
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    KnowledgeBase,
    User,
)
from app.rag.embeddings import EmbeddingService
from app.rag.retrieval import VectorSearchService

DIM = 1024


def _unit(*leading: float) -> list[float]:
    """构造 L2 归一化的 DIM 维向量，前若干位由参数给定，其余补零。"""

    vector = list(leading) + [0.0] * (DIM - len(leading))
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector]


VEC_EXACT = _unit(1.0)  # 与查询完全同向，余弦距离 0
VEC_NEAR = _unit(0.9, 0.1)  # 与查询高度相关
VEC_FAR = _unit(0.0, 1.0)  # 与查询正交，余弦距离 1


class StubEmbeddingProvider:
    """按文本返回预先指定的向量，让查询向量完全可控。"""

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    @property
    def model_name(self) -> str:
        return "stub-embedding"

    @property
    def dimension(self) -> int:
        return DIM

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._mapping[t] for t in texts]


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


def _chunk(document: Document, index: int, content: str, vector: Sequence[float]) -> DocumentChunk:
    return DocumentChunk(
        document=document,
        chunk_index=index,
        content=content,
        page_number=index + 1,
        section_title=f"第 {index + 1} 节",
        token_count=len(content),
        embedding=list(vector),
    )


@pytest.fixture
async def seeded_corpus(
    pg_engine: AsyncEngine,
) -> AsyncIterator[tuple[AsyncSession, KnowledgeBase]]:
    """建一个知识库：两篇 ready 文档 + 一篇 processing 文档（用于验证状态过滤）。"""

    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    session = session_factory()
    user = User(
        email=f"m1-05-{uuid4().hex}@example.test",
        password_hash="test-only",
        display_name="M1-05 integration",
    )
    knowledge_base = KnowledgeBase(owner=user, name=f"M1-05 {uuid4().hex}")

    ready_doc = Document(
        knowledge_base=knowledge_base,
        filename="handbook.txt",
        storage_path=f"m1-05/{uuid4().hex}.txt",
        mime_type="text/plain",
        size_bytes=128,
        sha256=uuid4().hex * 2,
        status=DocumentStatus.READY,
    )
    # 状态为 processing，其切片不应出现在检索结果里
    pending_doc = Document(
        knowledge_base=knowledge_base,
        filename="draft.txt",
        storage_path=f"m1-05/{uuid4().hex}.txt",
        mime_type="text/plain",
        size_bytes=64,
        sha256=uuid4().hex * 2,
        status=DocumentStatus.PROCESSING,
    )

    session.add_all(
        [
            _chunk(ready_doc, 0, "完全命中的片段", VEC_EXACT),
            _chunk(ready_doc, 1, "高度相关的片段", VEC_NEAR),
            _chunk(ready_doc, 2, "正交无关的片段", VEC_FAR),
            _chunk(pending_doc, 0, "未就绪文档的片段", VEC_EXACT),
        ]
    )
    await session.commit()

    user_id = user.id
    kb_id = knowledge_base.id
    try:
        yield session, knowledge_base
    finally:
        await session.rollback()
        await session.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
        await session.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
        await session.close()


def _service() -> VectorSearchService:
    provider = StubEmbeddingProvider({"查询": VEC_EXACT})
    return VectorSearchService(EmbeddingService(provider, dimension=DIM, batch_size=8))


@pytest.mark.integration
async def test_search_orders_by_cosine_similarity_and_carries_citation_metadata(
    seeded_corpus: tuple[AsyncSession, KnowledgeBase],
) -> None:
    session, knowledge_base = seeded_corpus

    results = await _service().search(session, knowledge_base.id, "查询", top_k=5)

    contents = [r.content for r in results]
    assert contents == ["完全命中的片段", "高度相关的片段", "正交无关的片段"]

    # 分数必须单调不增，且与手工计算的余弦相似度一致
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0, abs=1e-6)
    assert scores[1] == pytest.approx(0.9938837, abs=1e-5)
    assert scores[2] == pytest.approx(0.0, abs=1e-6)

    # 引用所需的元数据必须齐全，这是 M1-06 生成引用的基础
    top = results[0]
    assert top.document_name == "handbook.txt"
    assert top.chunk_index == 0
    assert top.page_number == 1
    assert top.section_title == "第 1 节"
    assert top.citation_label == "handbook.txt · Chunk 0 · 第 1 页 · 第 1 节"


@pytest.mark.integration
async def test_search_excludes_documents_that_are_not_ready(
    seeded_corpus: tuple[AsyncSession, KnowledgeBase],
) -> None:
    """processing/failed 文档可能残留上一版切片，绝不能被检索到。"""

    session, knowledge_base = seeded_corpus

    results = await _service().search(session, knowledge_base.id, "查询", top_k=10)

    assert all(r.document_name != "draft.txt" for r in results)
    assert "未就绪文档的片段" not in [r.content for r in results]


@pytest.mark.integration
async def test_min_score_is_pushed_down_so_low_scores_do_not_consume_top_k(
    seeded_corpus: tuple[AsyncSession, KnowledgeBase],
) -> None:
    """阈值若在 LIMIT 之后过滤，低分结果会占掉名额导致高分结果丢失。

    这里 top_k=2、阈值 0.5：正交片段（分数 0）必须在 SQL 层就被排除，
    使返回的两条都是合格结果，而不是"命中 + 高相关"被挤掉一条。
    """

    session, knowledge_base = seeded_corpus

    results = await _service().search(session, knowledge_base.id, "查询", top_k=2, min_score=0.5)

    assert len(results) == 2
    assert all(r.score >= 0.5 for r in results)
    assert [r.content for r in results] == ["完全命中的片段", "高度相关的片段"]


@pytest.mark.integration
async def test_hnsw_index_is_usable_by_the_cosine_operator(
    seeded_corpus: tuple[AsyncSession, KnowledgeBase],
) -> None:
    """确认 0002 建的 HNSW 索引与查询用的余弦算子匹配。

    算子与索引 ops 不一致时索引会被静默忽略、退化为全表扫描，而功能测试照样通过。
    小数据量下规划器本就倾向顺序扫描，因此这里关闭 seqscan 再看计划：
    只要计划里出现该索引，就说明 vector_cosine_ops 与 <=> 匹配。
    """

    session, _ = seeded_corpus
    literal = "[" + ",".join(str(v) for v in VEC_EXACT) + "]"

    await session.execute(text("SET LOCAL enable_seqscan = off"))
    plan_rows = await session.execute(
        text(
            "EXPLAIN SELECT id FROM document_chunks "
            f"ORDER BY embedding <=> '{literal}'::vector LIMIT 5"
        )
    )
    plan = "\n".join(row[0] for row in plan_rows)

    assert "ix_document_chunks_embedding_hnsw" in plan, plan
