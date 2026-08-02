from uuid import uuid4

import pytest

from app.rag.generation import REFUSAL_ANSWER, GroundedAnswerService
from app.rag.retrieval import SearchResult


def test_search_result_builds_human_readable_citation_label() -> None:
    result = SearchResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_name="员工制度.pdf",
        chunk_index=3,
        content="员工每年享有十天年假。",
        score=0.91,
        page_number=8,
        section_title="休假管理",
    )

    assert result.citation_label == "员工制度.pdf · Chunk 3 · 第 8 页 · 休假管理"


def test_search_result_label_works_without_location() -> None:
    result = SearchResult(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_name="policy.txt",
        chunk_index=0,
        content="内容",
        score=0.5,
        page_number=None,
        section_title=None,
    )

    assert result.citation_label == "policy.txt · Chunk 0"


@pytest.mark.parametrize("threshold", [-0.1, 1.1])
def test_grounded_service_rejects_invalid_confidence_threshold(threshold: float) -> None:
    with pytest.raises(ValueError, match="confidence_threshold"):
        GroundedAnswerService(object(), object(), confidence_threshold=threshold)  # type: ignore[arg-type]


def test_refusal_answer_is_explicit_and_grounded() -> None:
    assert "没有足够依据" in REFUSAL_ANSWER
