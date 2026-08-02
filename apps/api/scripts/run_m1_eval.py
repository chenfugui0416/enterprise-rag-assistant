"""M1-06 验收脚本：对演示语料跑预设问题，报告链路与检索表现。

用法（在 apps/api 下）：
    .venv/bin/python scripts/run_m1_eval.py

它会：
1. 建立（或复用）一个独立的评测知识库，索引 data/demo 下的演示文档；
2. 逐题调用 GroundedAnswerService，记录是否拒答、引用是否完整可回溯；
3. 对有依据的题目，判断标准来源是否出现在检索结果中（命中率）；
4. 打印汇总，并把结果写入 data/eval/last-run.json；
5. 结束后清理本次建立的数据。

重要：命中率只有在使用真实 embedding 时才有意义。mock provider 返回的是
确定性哈希向量，语义无关，其检索结果不能作为效果指标——脚本会在 mock 模式下
显式标注这一点，避免这些数字被误当成项目成绩。
"""

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
from app.rag.generation import GroundedAnswerService  # noqa: E402
from app.rag.loaders import load_document  # noqa: E402
from app.rag.providers.factory import build_llm_provider  # noqa: E402
from app.rag.retrieval import VectorSearchService  # noqa: E402

PROJECT_ROOT = API_ROOT.parents[1]
EVAL_FILE = PROJECT_ROOT / "data" / "eval" / "m1-questions.json"
RESULT_FILE = PROJECT_ROOT / "data" / "eval" / "last-run.json"
TOP_K = 5


def _load_eval() -> dict:
    return json.loads(EVAL_FILE.read_text(encoding="utf-8"))


async def _index_corpus(session, knowledge_base, corpus: list[str]) -> dict[str, int]:
    """索引语料，返回每个文件的 chunk 数。"""

    embedding_service = build_embedding_service()
    ingestion = DocumentIngestionService(embedding_service)
    counts: dict[str, int] = {}

    for relative in corpus:
        path = PROJECT_ROOT / relative
        parsed = load_document(path)
        document = Document(
            knowledge_base_id=knowledge_base.id,
            filename=path.name,
            storage_path=str(path),
            mime_type=parsed.media_type,
            size_bytes=path.stat().st_size,
            sha256=uuid4().hex * 2,
        )
        session.add(document)
        await session.commit()
        result = await ingestion.ingest(session, document.id, parsed)
        counts[path.name] = result.chunk_count
    return counts


def _evaluate_one(item: dict, answer, *, is_mock: bool) -> dict:
    """判定单题。

    有依据的题在 mock 下几乎必然被拒答——哈希向量与查询的相似度接近 0，
    低于置信阈值。那是 provider 的固有限制，不是链路缺陷，因此记为 limited
    而非 fail，避免把"待验证"粉饰成"已通过"，也避免把它误判成 bug。
    """

    sources = [c.document_name for c in answer.citations]
    contents = " ".join(c.content for c in answer.citations)

    record = {
        "id": item["id"],
        "question": item["question"],
        "answerable": item["answerable"],
        "refused": answer.refused,
        "retrieved_sources": sources,
        "top_score": round(answer.retrieved[0].score, 4) if answer.retrieved else None,
    }

    if item["answerable"]:
        record["expected_source"] = item["expected_source"]
        record["source_hit"] = item["expected_source"] in sources
        record["snippet_hit"] = bool(item["expected_snippet"]) and (
            item["expected_snippet"] in contents
        )
        record["has_traceable_citation"] = any(
            c.document_name and c.chunk_index is not None for c in answer.citations
        )
        if answer.refused and is_mock:
            record["verdict"] = "limited"
        elif not answer.refused and record["has_traceable_citation"]:
            record["verdict"] = "pass"
        else:
            record["verdict"] = "fail"
    else:
        # 无依据的题与语义能力无关：必须拒答且不给引用，mock 下同样可判定
        record["verdict"] = "pass" if (answer.refused and not answer.citations) else "fail"

    return record


async def main() -> int:
    settings = get_settings()
    dataset = _load_eval()

    # 不开 pool_pre_ping：脚本是短生命周期的单连接场景，而 pre_ping 在连接被
    # 复用时会跑在非 greenlet 上下文里，触发 MissingGreenlet。
    engine = create_async_engine(_async_database_url(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session = session_factory()

    user = User(
        email=f"eval-{uuid4().hex}@example.test",
        password_hash="eval-only",
        display_name="M1 评测",
    )
    knowledge_base = KnowledgeBase(owner=user, name=f"M1 评测 {uuid4().hex}")
    session.add(knowledge_base)
    await session.commit()

    is_mock = settings.embedding_provider == "mock"
    try:
        chunk_counts = await _index_corpus(session, knowledge_base, dataset["corpus"])
        service = GroundedAnswerService(
            VectorSearchService(build_embedding_service(settings)),
            build_llm_provider(settings),
        )

        records = []
        for item in dataset["questions"]:
            answer = await service.answer(session, knowledge_base.id, item["question"], top_k=TOP_K)
            records.append(_evaluate_one(item, answer, is_mock=is_mock))

        answerable = [r for r in records if r["answerable"]]
        unanswerable = [r for r in records if not r["answerable"]]
        source_hits = sum(1 for r in answerable if r["source_hit"])
        failed = [r for r in records if r["verdict"] == "fail"]
        limited = [r for r in records if r["verdict"] == "limited"]
        refusal_correct = sum(1 for r in unanswerable if r["verdict"] == "pass")

        summary = {
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model if not is_mock else "mock-embedding",
            "llm_provider": settings.llm_provider,
            "top_k": TOP_K,
            "chunk_counts": chunk_counts,
            "total_questions": len(records),
            "failed": len(failed),
            "limited_by_mock": len(limited),
            "refusal_correct": f"{refusal_correct}/{len(unanswerable)}",
            "source_hit_rate": f"{source_hits}/{len(answerable)}",
            "semantic_metrics_valid": not is_mock,
        }

        print("=" * 68)
        print("M1-06 验收结果")
        print("=" * 68)
        for record in records:
            mark = {"pass": "PASS", "fail": "FAIL", "limited": "LIMIT"}[record["verdict"]]
            kind = "有依据" if record["answerable"] else "无依据"
            extra = ""
            if record["answerable"]:
                extra = f" 命中={record['source_hit']} 来源={record['retrieved_sources'][:2]}"
            else:
                extra = f" 拒答={record['refused']}"
            print(f"[{mark}] {record['id']} ({kind}){extra}")

        print("-" * 68)
        print(f"失败题数          : {summary['failed']}")
        print(f"受 mock 限制未评估: {summary['limited_by_mock']}")
        print(f"无依据拒答正确    : {summary['refusal_correct']}")
        print(f"标准来源命中      : {summary['source_hit_rate']}")
        print(f"Embedding Provider: {summary['embedding_provider']}")

        if is_mock:
            print()
            print("!! 当前使用 mock embedding：确定性哈希向量，语义无关。")
            print("!! 上面的『标准来源命中』不代表检索效果，不得写入简历或 RESUME_EVIDENCE。")
            print("!! 配置真实 EMBEDDING_API_KEY 后重跑本脚本才能得到有效指标。")

        RESULT_FILE.write_text(
            json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n结果已写入 {RESULT_FILE.relative_to(PROJECT_ROOT)}")

        # 只有真正的失败才算不通过；limited 表示待真实 provider 验证
        return 0 if not failed else 1
    finally:
        kb_id, user_id = knowledge_base.id, user.id
        await session.rollback()
        await session.close()
        # 用全新会话清理：主流程可能已让原会话处于异常事务状态
        async with session_factory() as cleanup:
            await cleanup.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
            await cleanup.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
            await cleanup.execute(delete(User).where(User.id == user_id))
            await cleanup.commit()
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
