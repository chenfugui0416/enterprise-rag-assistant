"""按配置装配 Provider。调用方只拿到协议类型，看不到具体实现。"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings

from .base import EmbeddingProvider, LLMProvider
from .mock import MockEmbeddingProvider, MockLLMProvider
from .openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleLLMProvider,
)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "mock":
        return MockEmbeddingProvider(dimension=settings.embedding_dim)
    return OpenAICompatibleEmbeddingProvider(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        dimension=settings.embedding_dim,
        batch_size=settings.embedding_batch_size,
    )


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "mock":
        return MockLLMProvider()
    return OpenAICompatibleLLMProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return build_embedding_provider(get_settings())


@lru_cache
def get_llm_provider() -> LLMProvider:
    return build_llm_provider(get_settings())
