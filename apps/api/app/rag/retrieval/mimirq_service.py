"""MimirQ Search Service adapter for Route B (Microservice integration mode).

Implements the same search contract as VectorSearchService so GroundedAnswerService
can use MimirQ's hybrid retrieval and re-ranking without changing a single line of business logic.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.rag.retrieval.mimirq_client import MimirQClient
from app.rag.retrieval.service import SearchResult

logger = logging.getLogger(__name__)


def _to_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    s = str(val or "").strip()
    try:
        return UUID(s)
    except (ValueError, AttributeError):
        return uuid5(NAMESPACE_URL, s or "mimirq-default-id")


class MimirQSearchService:
    """Delegates retrieval to MimirQ enterprise RAG middle platform via REST API."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: MimirQClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or MimirQClient(
            base_url=self.settings.mimirq_base_url,
            username=self.settings.mimirq_username,
            password=self.settings.mimirq_password,
            timeout_seconds=self.settings.mimirq_timeout_seconds,
        )
        self.default_dataset_id = self.settings.mimirq_dataset_id

    async def search(
        self,
        session: AsyncSession,
        knowledge_base_id: UUID,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> tuple[SearchResult, ...]:
        """Search MimirQ and map returned citations to SearchResult tuples."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty")
        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0 and 1")

        # Use configured default dataset or map knowledge_base_id
        target_dataset_id = self.default_dataset_id or str(knowledge_base_id)

        logger.info(
            "Delegating search to MimirQ [dataset=%s, top_k=%d, min_score=%.2f]: %s",
            target_dataset_id,
            top_k,
            min_score,
            normalized_query,
        )

        raw_citations = await self.client.retrieve(
            query=normalized_query,
            dataset_id=target_dataset_id,
            top_k=top_k,
            min_score=min_score,
            retrieval_mode="hybrid",
        )

        results: list[SearchResult] = []
        for index, citation in enumerate(raw_citations):
            chunk_id = _to_uuid(citation.get("chunk_id") or f"chunk-{index}")
            doc_id = _to_uuid(citation.get("document_id") or f"doc-{index}")
            raw_doc_name = citation.get("document_name") or citation.get("source")
            doc_name = str(raw_doc_name or "企业制度文档")
            chunk_index = int(citation.get("chunk_index") or index)
            content = str(citation.get("chunk_content") or "")

            raw_score = (
                citation.get("rerank_score_final")
                or citation.get("rerank_score")
                or citation.get("relevance_score")
                or citation.get("vector_score")
                or 0.0
            )
            score = max(0.0, min(1.0, float(raw_score)))

            page_number = citation.get("page_number")
            if page_number is not None:
                try:
                    page_number = int(page_number)
                except (ValueError, TypeError):
                    page_number = None

            section_title = citation.get("header_path") or citation.get("section_title")
            if section_title is not None:
                section_title = str(section_title)

            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    document_name=doc_name,
                    chunk_index=chunk_index,
                    content=content,
                    score=score,
                    page_number=page_number,
                    section_title=section_title,
                )
            )

        return tuple(results)
