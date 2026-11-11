"""RAG Benchmark CLI: executes automated IR & anti-hallucination evaluation across strategies."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import delete  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import _async_database_url  # noqa: E402
from app.models import Document, KnowledgeBase, User  # noqa: E402
from app.rag.embeddings import DocumentIngestionService, build_embedding_service  # noqa: E402
from app.rag.evaluation.evaluator import RAGEvaluator  # noqa: E402
from app.rag.generation.service import GroundedAnswerService  # noqa: E402
from app.rag.loaders import load_document  # noqa: E402
from app.rag.providers.factory import build_llm_provider  # noqa: E402
from app.rag.retrieval import MimirQSearchService, VectorSearchService  # noqa: E402

PROJECT_ROOT = API_ROOT.parents[1]
EVAL_FILE = PROJECT_ROOT / "data" / "eval" / "m1-questions.json"
REPORT_FILE = PROJECT_ROOT / "data" / "eval" / "benchmark_report.md"


def _load_eval_dataset() -> dict:
    return json.loads(EVAL_FILE.read_text(encoding="utf-8"))


async def _index_demo_corpus(session, knowledge_base: KnowledgeBase, corpus: list[str]) -> None:
    embedding_service = build_embedding_service()
    ingestion = DocumentIngestionService(embedding_service)

    for rel_path in corpus:
        doc_path = PROJECT_ROOT / rel_path
        parsed = load_document(doc_path)
        doc = Document(
            knowledge_base_id=knowledge_base.id,
            filename=doc_path.name,
            storage_path=str(doc_path),
            mime_type=parsed.media_type,
            size_bytes=doc_path.stat().st_size,
            sha256=uuid4().hex * 2,
        )
        session.add(doc)
        await session.commit()
        await ingestion.ingest(session, doc.id, parsed)


async def main() -> int:
    settings = get_settings()
    dataset = _load_eval_dataset()

    engine = create_async_engine(_async_database_url(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session = session_factory()

    user = User(
        email=f"benchmark-{uuid4().hex}@example.test",
        password_hash="eval-only",
        display_name="Benchmark Evaluator",
    )
    knowledge_base = KnowledgeBase(owner=user, name=f"Benchmark-KB-{uuid4().hex[:8]}")
    session.add(knowledge_base)
    await session.commit()

    summaries = []
    try:
        await _index_demo_corpus(session, knowledge_base, dataset["corpus"])
        llm_provider = build_llm_provider(settings)

        # 1. 评估原生向量检索策略 (Dense Vector)
        vector_service = VectorSearchService(build_embedding_service(settings))
        vector_answer_service = GroundedAnswerService(
            vector_service,
            llm_provider,
            confidence_threshold=0.35,
        )
        vector_evaluator = RAGEvaluator(vector_answer_service, mode_label="Naive Vector (Dense)")
        print("\n[1/2] 正在评测 Naive Vector (Dense) 策略...")
        vector_summary = await vector_evaluator.run_benchmark(
            session,
            knowledge_base.id,
            dataset,
            top_k=5,
        )
        summaries.append(vector_summary)

        # 2. 如果开启或支持 MimirQ，评估多路混合检索中台策略 (Hybrid BM25 + Vector)
        if settings.mimirq_enabled:
            print("\n[2/2] 正在评测 MimirQ Hybrid (BM25 + Dense + Rerank) 策略...")
            mimirq_service = MimirQSearchService(settings)
            mimirq_answer_service = GroundedAnswerService(
                mimirq_service,
                llm_provider,
                confidence_threshold=0.35,
            )
            mimirq_evaluator = RAGEvaluator(
                mimirq_answer_service,
                mode_label="MimirQ Hybrid (BM25+Dense+Rerank)",
            )
            mimirq_summary = await mimirq_evaluator.run_benchmark(
                session,
                knowledge_base.id,
                dataset,
                top_k=5,
            )
            summaries.append(mimirq_summary)

        # 渲染对比报告
        report_markdown = RAGEvaluator.render_comparison_markdown(summaries)
        REPORT_FILE.write_text(report_markdown, encoding="utf-8")

        print("\n" + "=" * 78)
        print(report_markdown)
        print("=" * 78)
        print(f"\n完整评测对比报告已保存至：{REPORT_FILE.relative_to(PROJECT_ROOT)}\n")
        return 0

    finally:
        kb_id, user_id = knowledge_base.id, user.id
        await session.rollback()
        await session.close()
        async with session_factory() as cleanup:
            await cleanup.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
            await cleanup.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
            await cleanup.execute(delete(User).where(User.id == user_id))
            await cleanup.commit()
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
