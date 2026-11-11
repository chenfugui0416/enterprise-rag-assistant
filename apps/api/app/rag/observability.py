"""Lightweight observability and execution tracing for RAG & Agent pipelines."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ExecutionTrace:
    """Immutable snapshot of an end-to-end RAG query execution."""

    trace_id: str
    total_duration_ms: float
    retrieval_mode: str
    retrieval_duration_ms: float
    retrieved_count: int
    top_score: float | None
    llm_duration_ms: float
    refused: bool
    spans: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "retrieval_mode": self.retrieval_mode,
            "retrieval_duration_ms": round(self.retrieval_duration_ms, 2),
            "retrieved_count": self.retrieved_count,
            "top_score": (round(self.top_score, 4) if self.top_score is not None else None),
            "llm_duration_ms": round(self.llm_duration_ms, 2),
            "refused": self.refused,
            "spans": {k: round(v, 2) for k, v in self.spans.items()},
            "metadata": self.metadata,
        }


class ExecutionTracer:
    """Collects step timings and telemetry for a single query."""

    def __init__(
        self,
        *,
        trace_id: str | None = None,
        retrieval_mode: str = "vector",
    ) -> None:
        self.trace_id = trace_id or uuid4().hex
        self.retrieval_mode = retrieval_mode
        self._start_perf = time.perf_counter()
        self.retrieval_duration_ms = 0.0
        self.retrieved_count = 0
        self.top_score: float | None = None
        self.llm_duration_ms = 0.0
        self.refused = False
        self.spans: dict[str, float] = {}
        self.metadata: dict[str, Any] = {}

    @contextmanager
    def span(self, name: str) -> Generator[None, None, None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self.spans[name] = elapsed_ms

    def record_retrieval(
        self,
        *,
        duration_ms: float,
        count: int,
        top_score: float | None = None,
        mode: str | None = None,
    ) -> None:
        self.retrieval_duration_ms = duration_ms
        self.retrieved_count = count
        self.top_score = top_score
        if mode:
            self.retrieval_mode = mode

    def record_llm(self, *, duration_ms: float, refused: bool) -> None:
        self.llm_duration_ms = duration_ms
        self.refused = refused

    def finish(self) -> ExecutionTrace:
        total_ms = (time.perf_counter() - self._start_perf) * 1000.0
        return ExecutionTrace(
            trace_id=self.trace_id,
            total_duration_ms=total_ms,
            retrieval_mode=self.retrieval_mode,
            retrieval_duration_ms=self.retrieval_duration_ms,
            retrieved_count=self.retrieved_count,
            top_score=self.top_score,
            llm_duration_ms=self.llm_duration_ms,
            refused=self.refused,
            spans=dict(self.spans),
            metadata=dict(self.metadata),
        )
