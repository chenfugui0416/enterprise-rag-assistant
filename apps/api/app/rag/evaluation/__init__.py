"""Evaluation, IR metrics, and benchmarking framework for enterprise RAG."""

from app.rag.evaluation.evaluator import RAGEvaluator
from app.rag.evaluation.metrics import (
    BenchmarkSummary,
    EvaluationRecord,
    hit_rate_at_k,
    reciprocal_rank,
    refusal_correctness,
)

__all__ = [
    "BenchmarkSummary",
    "EvaluationRecord",
    "RAGEvaluator",
    "hit_rate_at_k",
    "reciprocal_rank",
    "refusal_correctness",
]
