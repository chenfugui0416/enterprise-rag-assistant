"""Standard Information Retrieval (IR) and Groundedness metrics for RAG evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


def hit_rate_at_k(retrieved_sources: Sequence[str], expected_source: str, k: int = 5) -> bool:
    """Returns True if expected_source is present within top-k retrieved sources."""
    if not expected_source or not retrieved_sources:
        return False
    return expected_source in retrieved_sources[:k]


def reciprocal_rank(retrieved_sources: Sequence[str], expected_source: str) -> float:
    """Calculates reciprocal rank (1/rank) for the expected source.

    Returns 0.0 if not found.
    """
    if not expected_source or not retrieved_sources:
        return 0.0
    for rank, source in enumerate(retrieved_sources, start=1):
        if source == expected_source:
            return 1.0 / rank
    return 0.0


def refusal_correctness(refused: bool, answerable: bool) -> bool:
    """Strictly checks anti-hallucination behavior.

    - Answerable question must NOT be refused (when evidence is sufficient).
    - Unanswerable question MUST be refused.
    """
    if not answerable:
        return refused
    return not refused


@dataclass(slots=True)
class EvaluationRecord:
    query_id: str
    question: str
    answerable: bool
    expected_source: str | None
    retrieved_sources: list[str]
    refused: bool
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float
    retrieval_duration_ms: float
    total_duration_ms: float
    top_score: float | None = None
    has_valid_citations: bool = False
    verdict: str = "pass"


@dataclass(slots=True)
class BenchmarkSummary:
    evaluator_name: str
    retrieval_mode: str
    total_queries: int
    answerable_count: int
    unanswerable_count: int
    hit_rate_at_1: float
    hit_rate_at_3: float
    hit_rate_at_5: float
    mrr: float
    refusal_accuracy: float
    avg_retrieval_duration_ms: float
    avg_total_duration_ms: float
    records: list[EvaluationRecord] = field(default_factory=list)

    @classmethod
    def from_records(
        cls,
        *,
        evaluator_name: str,
        retrieval_mode: str,
        records: list[EvaluationRecord],
    ) -> BenchmarkSummary:
        total = len(records)
        answerable = [r for r in records if r.answerable]
        unanswerable = [r for r in records if not r.answerable]

        ans_count = len(answerable)
        hit_1 = (sum(1 for r in answerable if r.hit_at_1) / ans_count) if ans_count > 0 else 0.0
        hit_3 = (sum(1 for r in answerable if r.hit_at_3) / ans_count) if ans_count > 0 else 0.0
        hit_5 = (sum(1 for r in answerable if r.hit_at_5) / ans_count) if ans_count > 0 else 0.0
        mrr = (sum(r.reciprocal_rank for r in answerable) / ans_count) if ans_count > 0 else 0.0

        unans_count = len(unanswerable)
        refusal_acc = (
            (sum(1 for r in unanswerable if r.refused) / unans_count) if unans_count > 0 else 1.0
        )

        avg_retrieval = (
            (sum(r.retrieval_duration_ms for r in records) / total) if total > 0 else 0.0
        )
        avg_total = (sum(r.total_duration_ms for r in records) / total) if total > 0 else 0.0

        return cls(
            evaluator_name=evaluator_name,
            retrieval_mode=retrieval_mode,
            total_queries=total,
            answerable_count=ans_count,
            unanswerable_count=unans_count,
            hit_rate_at_1=round(hit_1 * 100, 2),
            hit_rate_at_3=round(hit_3 * 100, 2),
            hit_rate_at_5=round(hit_5 * 100, 2),
            mrr=round(mrr, 4),
            refusal_accuracy=round(refusal_acc * 100, 2),
            avg_retrieval_duration_ms=round(avg_retrieval, 2),
            avg_total_duration_ms=round(avg_total, 2),
            records=records,
        )

    def to_markdown_table(self) -> str:
        headers = (
            "| 模式 / 指标 | Hit Rate@1 | Hit Rate@3 | Hit Rate@5 | "
            "MRR | 拒答准确率 | 检索均耗时 | 总均耗时 |\n"
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
        )
        data = (
            f"| **{self.retrieval_mode}** | {self.hit_rate_at_1}% | {self.hit_rate_at_3}% | "
            f"{self.hit_rate_at_5}% | {self.mrr} | {self.refusal_accuracy}% | "
            f"{self.avg_retrieval_duration_ms}ms | {self.avg_total_duration_ms}ms |"
        )
        return headers + data
