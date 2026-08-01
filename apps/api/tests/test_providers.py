"""Provider 层测试。

Mock provider 的价值在于确定性，这里就针对确定性、维度和归一化做断言；
一旦有人把 mock 改成随机实现，依赖它的管线测试会立刻失去意义，所以这些
断言是防回归的第一道闸门。
"""

import math

import pytest

from app.core.config import Settings
from app.rag.providers.base import EmbeddingProvider, LLMProvider
from app.rag.providers.factory import build_embedding_provider, build_llm_provider
from app.rag.providers.mock import MockEmbeddingProvider, MockLLMProvider


async def test_mock_embedding_is_deterministic() -> None:
    provider = MockEmbeddingProvider(dimension=64)
    first = await provider.embed(["员工年假制度"])
    second = await provider.embed(["员工年假制度"])
    assert first == second


async def test_mock_embedding_distinguishes_texts() -> None:
    provider = MockEmbeddingProvider(dimension=64)
    vectors = await provider.embed(["报销流程", "年假制度"])
    assert vectors[0] != vectors[1]


@pytest.mark.parametrize("dimension", [8, 64, 1024])
async def test_mock_embedding_shape_and_norm(dimension: int) -> None:
    provider = MockEmbeddingProvider(dimension=dimension)
    (vector,) = await provider.embed(["任意文本"])
    assert len(vector) == dimension
    # L2 归一化后模长为 1，使余弦相似度等价于内积
    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)


async def test_mock_embedding_preserves_order() -> None:
    provider = MockEmbeddingProvider(dimension=16)
    texts = [f"文档片段 {i}" for i in range(5)]
    vectors = await provider.embed(texts)
    expected = [(await provider.embed([t]))[0] for t in texts]
    assert vectors == expected


def test_mock_embedding_rejects_invalid_dimension() -> None:
    with pytest.raises(ValueError):
        MockEmbeddingProvider(dimension=0)


async def test_mock_llm_echoes_last_user_message() -> None:
    provider = MockLLMProvider()
    answer = await provider.complete(
        [
            {"role": "system", "content": "你是企业知识库助手"},
            {"role": "user", "content": "年假有几天"},
        ]
    )
    assert "年假有几天" in answer


async def test_mock_llm_stream_concatenates_to_complete() -> None:
    provider = MockLLMProvider()
    messages = [{"role": "user", "content": "报销需要哪些材料"}]
    streamed = "".join([chunk async for chunk in provider.stream(messages)])
    assert streamed == await provider.complete(messages)


def test_factory_returns_mock_by_default() -> None:
    settings = Settings(llm_provider="mock", embedding_provider="mock", embedding_dim=32)
    embedder = build_embedding_provider(settings)
    llm = build_llm_provider(settings)
    assert isinstance(embedder, EmbeddingProvider)
    assert isinstance(llm, LLMProvider)
    assert embedder.dimension == 32
    assert embedder.model_name == "mock-embedding"


def test_factory_rejects_openai_provider_without_key() -> None:
    """缺 key 时必须在装配阶段就失败，而不是等到线上第一次请求才报错。"""
    settings = Settings(embedding_provider="openai_compatible", embedding_api_key="")
    with pytest.raises(ValueError, match="EMBEDDING_API_KEY"):
        build_embedding_provider(settings)
