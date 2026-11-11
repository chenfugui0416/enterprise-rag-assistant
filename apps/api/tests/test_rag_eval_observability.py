"""Unit and integration tests for RAG observability, telemetry, and evaluation metrics."""

from __future__ import annotations

import time
from uuid import uuid4

from app.rag.evaluation.evaluator import RAGEvaluator
from app.rag.evaluation.metrics import (
    BenchmarkSummary,
    EvaluationRecord,
    hit_rate_at_k,
    reciprocal_rank,
    refusal_correctness,
)
from app.rag.generation.service import AnswerResult, Citation
from app.rag.observability import ExecutionTrace, ExecutionTracer
from app.rag.retrieval.service import SearchResult


def test_execution_tracer_lifecycle() -> None:
    tracer = ExecutionTracer(retrieval_mode="mimirq_hybrid")
    assert tracer.retrieval_mode == "mimirq_hybrid"

    with tracer.span("custom_step"):
        time.sleep(0.005)

    tracer.record_retrieval(duration_ms=12.5, count=3, top_score=0.88)
    tracer.record_llm(duration_ms=45.2, refused=False)

    trace = tracer.finish()
    assert isinstance(trace, ExecutionTrace)
    assert trace.retrieval_mode == "mimirq_hybrid"
    assert trace.retrieval_duration_ms == 12.5
    assert trace.retrieved_count == 3
    assert trace.top_score == 0.88
    assert trace.llm_duration_ms == 45.2
    assert not trace.refused
    assert "custom_step" in trace.spans
    assert trace.spans["custom_step"] >= 4.0
    assert trace.total_duration_ms >= 4.0

    as_dict = trace.to_dict()
    assert as_dict["retrieval_mode"] == "mimirq_hybrid"
    assert as_dict["top_score"] == 0.88


def test_hit_rate_at_k() -> None:
    retrieved = ["doc_a.md", "doc_b.md", "doc_c.md"]

    assert hit_rate_at_k(retrieved, "doc_a.md", k=1) is True
    assert hit_rate_at_k(retrieved, "doc_b.md", k=1) is False
    assert hit_rate_at_k(retrieved, "doc_b.md", k=2) is True
    assert hit_rate_at_k(retrieved, "doc_c.md", k=3) is True
    assert hit_rate_at_k(retrieved, "doc_d.md", k=5) is False
    assert hit_rate_at_k([], "doc_a.md", k=5) is False
    assert hit_rate_at_k(retrieved, "", k=5) is False


def test_reciprocal_rank() -> None:
    retrieved = ["doc_a.md", "doc_b.md", "doc_c.md"]

    assert reciprocal_rank(retrieved, "doc_a.md") == 1.0
    assert reciprocal_rank(retrieved, "doc_b.md") == 0.5
    assert round(reciprocal_rank(retrieved, "doc_c.md"), 3) == 0.333
    assert reciprocal_rank(retrieved, "missing.md") == 0.0
    assert reciprocal_rank([], "doc_a.md") == 0.0


def test_refusal_correctness() -> None:
    # When question is unanswerable:
    assert refusal_correctness(refused=True, answerable=False) is True
    assert refusal_correctness(refused=False, answerable=False) is False

    # When question is answerable:
    assert refusal_correctness(refused=False, answerable=True) is True
    assert refusal_correctness(refused=True, answerable=True) is False


def test_benchmark_summary_aggregation() -> None:
    records = [
        EvaluationRecord(
            query_id="Q1",
            question="问题 1",
            answerable=True,
            expected_source="doc1.md",
            retrieved_sources=["doc1.md", "doc2.md"],
            refused=False,
            hit_at_1=True,
            hit_at_3=True,
            hit_at_5=True,
            reciprocal_rank=1.0,
            retrieval_duration_ms=10.0,
            total_duration_ms=100.0,
        ),
        EvaluationRecord(
            query_id="Q2",
            question="问题 2",
            answerable=True,
            expected_source="doc2.md",
            retrieved_sources=["doc1.md", "doc2.md"],
            refused=False,
            hit_at_1=False,
            hit_at_3=True,
            hit_at_5=True,
            reciprocal_rank=0.5,
            retrieval_duration_ms=20.0,
            total_duration_ms=200.0,
        ),
        EvaluationRecord(
            query_id="Q3",
            question="负样本问题",
            answerable=False,
            expected_source=None,
            retrieved_sources=[],
            refused=True,
            hit_at_1=False,
            hit_at_3=False,
            hit_at_5=False,
            reciprocal_rank=0.0,
            retrieval_duration_ms=5.0,
            total_duration_ms=5.0,
        ),
    ]

    summary = BenchmarkSummary.from_records(
        evaluator_name="TestEvaluator",
        retrieval_mode="mimirq_hybrid",
        records=records,
    )

    assert summary.total_queries == 3
    assert summary.answerable_count == 2
    assert summary.unanswerable_count == 1
    assert summary.hit_rate_at_1 == 50.0
    assert summary.hit_rate_at_3 == 100.0
    assert summary.hit_rate_at_5 == 100.0
    assert summary.mrr == 0.75
    assert summary.refusal_accuracy == 100.0
    assert round(summary.avg_retrieval_duration_ms, 1) == 11.7

    md_table = summary.to_markdown_table()
    assert "mimirq_hybrid" in md_table
    assert "100.0%" in md_table


def test_evaluator_evaluate_single_result() -> None:
    evaluator = RAGEvaluator(None, mode_label="mimirq_hybrid")  # type: ignore[arg-type]
    doc_id = uuid4()
    chunk_id = uuid4()
    citation = Citation(
        document_id=doc_id,
        document_name="employee-handbook.md",
        chunk_index=0,
        score=0.92,
        page_number=1,
        section_title="年假政策",
        content="十天带薪年假",
    )
    search_result = SearchResult(
        document_id=doc_id,
        chunk_id=chunk_id,
        document_name="employee-handbook.md",
        chunk_index=0,
        score=0.92,
        page_number=1,
        section_title="年假政策",
        content="十天带薪年假",
    )
    answer = AnswerResult(
        question="带薪年假多少天？",
        answer="员工享有十天带薪年假。",
        citations=(citation,),
        retrieved=(search_result,),
        refused=False,
        model_name="mock-model",
    )

    item = {
        "id": "Q01",
        "question": "带薪年假多少天？",
        "answerable": True,
        "expected_source": "employee-handbook.md",
    }

    record = evaluator.evaluate_single_result(item, answer, retrieval_ms=15.0, total_ms=120.0)
    assert record.hit_at_1 is True
    assert record.hit_at_3 is True
    assert record.reciprocal_rank == 1.0
    assert record.verdict == "pass"

    # Test rendering comparison markdown
    summary = BenchmarkSummary.from_records(
        evaluator_name="Test",
        retrieval_mode="mimirq_hybrid",
        records=[record],
    )
    report_md = RAGEvaluator.render_comparison_markdown([summary])
    assert "# 企业级 RAG 检索策略 A/B 基准评测对比报告" in report_md
    assert "mimirq_hybrid" in report_md


def test_query_request_schema_with_history_and_agent() -> None:
    from app.schemas.demo_rag import ChatMessageRequest, QueryRequest

    req = QueryRequest(
        question="还有几天假？",
        use_agent=True,
        history=(
            ChatMessageRequest(role="user", content="我有多少天年假？"),
            ChatMessageRequest(role="assistant", content="你有十天年假。"),
        ),
    )
    assert req.use_agent is True
    assert len(req.history) == 2
    assert req.history[0].role == "user"
    assert req.history[1].content == "你有十天年假。"
