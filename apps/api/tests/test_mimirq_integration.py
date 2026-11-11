"""Unit and integration tests for MimirQ client and search service adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.rag.generation import GroundedAnswerService
from app.rag.providers.mock import MockLLMProvider
from app.rag.retrieval import MimirQClient, MimirQSearchService, SearchResult


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        mimirq_enabled=True,
        mimirq_base_url="http://mock-mimirq:8000",
        mimirq_username="test_admin",
        mimirq_password="test_password",
        mimirq_dataset_id="2b30cca0-7e31-4893-83bd-75544b33f13c",
    )


@pytest.mark.asyncio
async def test_mimirq_client_login_and_token_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MimirQClient(
        base_url="http://mock-mimirq:8000",
        username="test_admin",
        password="test_password",
    )

    login_call_count = 0

    def mock_post(url: str, *args, **kwargs) -> httpx.Response:
        nonlocal login_call_count
        if "/api/v1/auth/login" in str(url):
            login_call_count += 1
            return httpx.Response(
                200,
                json={"token": {"access_token": "fake-jwt-token-123", "expires_in": 3600}},
                request=httpx.Request("POST", url),
            )
        if "/api/v1/rag/retrieve" in str(url):
            return httpx.Response(
                200,
                json={
                    "citations": [
                        {
                            "chunk_id": str(uuid4()),
                            "document_id": str(uuid4()),
                            "document_name": "差旅报销管理制度.docx",
                            "chunk_index": 1,
                            "chunk_content": "住宿标准：一线城市标准上限为 500 元/天。",
                            "rerank_score": 0.95,
                            "page_number": 3,
                            "header_path": "第三章 住宿标准",
                        }
                    ]
                },
                request=httpx.Request("POST", url),
            )
        return httpx.Response(404, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", AsyncMock(side_effect=mock_post))

    dataset_id = "2b30cca0-7e31-4893-83bd-75544b33f13c"
    # First retrieval: should login and cache token
    results = await client.retrieve("一线城市住宿费标准是多少？", dataset_id=dataset_id)
    assert len(results) == 1
    assert results[0]["document_name"] == "差旅报销管理制度.docx"
    assert results[0]["rerank_score"] == 0.95
    assert login_call_count == 1

    # Second retrieval: token should be reused without re-login
    results2 = await client.retrieve("二线城市住宿标准？", dataset_id=dataset_id)
    assert len(results2) == 1
    assert login_call_count == 1


@pytest.mark.asyncio
async def test_mimirq_search_service_search_mapping(mock_settings: Settings) -> None:
    mock_client = MagicMock(spec=MimirQClient)
    test_chunk_id = uuid4()
    test_doc_id = uuid4()

    mock_client.retrieve = AsyncMock(
        return_value=[
            {
                "chunk_id": str(test_chunk_id),
                "document_id": str(test_doc_id),
                "document_name": "员工考勤管理办法.pdf",
                "chunk_index": 2,
                "chunk_content": "年假计算规则：工作满1年不满10年者，每年年休假为5天。",
                "rerank_score": 0.88,
                "page_number": 4,
                "header_path": "第二章 年休假管理",
            }
        ]
    )

    service = MimirQSearchService(settings=mock_settings, client=mock_client)
    mock_session = AsyncMock()

    results = await service.search(
        session=mock_session,
        knowledge_base_id=uuid4(),
        query="工作满一年有多少天年假？",
        top_k=3,
        min_score=0.5,
    )

    assert len(results) == 1
    result = results[0]
    assert isinstance(result, SearchResult)
    assert result.chunk_id == test_chunk_id
    assert result.document_id == test_doc_id
    assert result.document_name == "员工考勤管理办法.pdf"
    assert result.chunk_index == 2
    assert "年休假为5天" in result.content
    assert result.score == 0.88
    assert result.page_number == 4
    assert result.section_title == "第二章 年休假管理"
    assert "第 4 页 · 第二章 年休假管理" in result.citation_label


@pytest.mark.asyncio
async def test_grounded_answer_service_with_mimirq(mock_settings: Settings) -> None:
    mock_client = MagicMock(spec=MimirQClient)
    mock_client.retrieve = AsyncMock(
        return_value=[
            {
                "chunk_id": str(uuid4()),
                "document_id": str(uuid4()),
                "document_name": "企业财务制度.docx",
                "chunk_index": 0,
                "chunk_content": "发票报销时限：员工应于消费后30个自然日内完成系统报销审批提交。",
                "rerank_score": 0.92,
                "page_number": 1,
                "header_path": "发票与报销时限",
            }
        ]
    )

    search_service = MimirQSearchService(settings=mock_settings, client=mock_client)
    llm_provider = MockLLMProvider()
    answer_service = GroundedAnswerService(
        search_service=search_service,
        llm_provider=llm_provider,
        confidence_threshold=0.35,
    )

    mock_session = AsyncMock()
    answer = await answer_service.answer(
        session=mock_session,
        knowledge_base_id=uuid4(),
        question="发票报销的最晚时限是几天？",
        top_k=3,
    )

    assert not answer.refused
    assert len(answer.citations) == 1
    assert answer.citations[0].document_name == "企业财务制度.docx"
    assert answer.citations[0].score == 0.92
    assert "发票报销时限" in answer.answer or len(answer.answer) > 0


@pytest.mark.asyncio
async def test_grounded_answer_service_refusal_when_mimirq_empty(mock_settings: Settings) -> None:
    mock_client = MagicMock(spec=MimirQClient)
    # Return empty citations (or below confidence threshold)
    mock_client.retrieve = AsyncMock(return_value=[])

    search_service = MimirQSearchService(settings=mock_settings, client=mock_client)
    llm_provider = MockLLMProvider()
    answer_service = GroundedAnswerService(
        search_service=search_service,
        llm_provider=llm_provider,
        confidence_threshold=0.5,
    )

    mock_session = AsyncMock()
    answer = await answer_service.answer(
        session=mock_session,
        knowledge_base_id=uuid4(),
        question="火星探测器发射计划是什么？",
    )

    assert answer.refused
    assert len(answer.citations) == 0
    assert "现有知识库中没有足够依据" in answer.answer
