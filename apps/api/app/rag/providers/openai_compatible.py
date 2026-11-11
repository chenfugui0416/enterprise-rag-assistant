"""OpenAI 兼容 Provider：适用于 SiliconFlow、DeepSeek、通义、vLLM 等任何
暴露 /chat/completions 与 /embeddings 的服务。
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx

from .base import ProviderError, ToolCall, ToolCallResult


def _make_http_client(timeout: float) -> httpx.AsyncClient:
    proxy = (
        os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
    )
    return httpx.AsyncClient(timeout=timeout, proxy=proxy, trust_env=False)


def _redact(exc: Exception) -> str:
    """异常信息可能包含 URL 与请求头，这里只保留类型和状态码。"""
    if isinstance(exc, httpx.HTTPStatusError):
        return f"upstream returned HTTP {exc.response.status_code}"
    return type(exc).__name__


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        dimension: int,
        batch_size: int = 32,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY is required for openai_compatible provider")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._batch_size = max(1, batch_size)
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "OpenCode/1.0.0",
        }
        async with _make_http_client(self._timeout) as client:
            for start in range(0, len(texts), self._batch_size):
                batch = texts[start : start + self._batch_size]
                try:
                    resp = await client.post(
                        f"{self._base_url}/embeddings",
                        headers=headers,
                        json={"model": self._model, "input": batch},
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                except Exception as exc:  # noqa: BLE001 - 统一收敛为 ProviderError
                    raise ProviderError(f"embedding request failed: {_redact(exc)}") from None

                # 上游不保证返回顺序，按 index 排序后再取值。
                items = sorted(payload["data"], key=lambda d: d.get("index", 0))
                for item in items:
                    vec = item["embedding"]
                    if len(vec) != self._dimension:
                        raise ProviderError(
                            f"embedding dimension mismatch: expected {self._dimension}, "
                            f"got {len(vec)}; check EMBEDDING_DIM"
                        )
                    vectors.append(vec)
        return vectors


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("LLM_API_KEY is required for openai_compatible provider")
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    def _payload(
        self,
        messages: list[dict[str, object]],
        stream: bool,
        tools: list[dict[str, object]] | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    async def complete(self, messages: list[dict[str, str]]) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "OpenCode/1.0.0",
        }
        try:
            async with _make_http_client(self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=self._payload(messages, stream=False),
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"completion request failed: {_redact(exc)}") from None
        return data["choices"][0]["message"]["content"]

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "OpenCode/1.0.0",
        }
        try:
            async with (
                _make_http_client(self._timeout) as client,
                client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=self._payload(messages, stream=True),
                ) as resp,
            ):
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[len("data:") :].strip()
                    if not chunk or chunk == "[DONE]":
                        continue
                    delta = json.loads(chunk)["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        yield content
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"streaming request failed: {_redact(exc)}") from None

    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ToolCallResult:
        """带工具定义的一次生成，解析 OpenAI 兼容的 tool_calls 结构（ADR-0011）。"""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "OpenCode/1.0.0",
        }
        try:
            async with _make_http_client(self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=self._payload(messages, stream=False, tools=tools),
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"tool-calling request failed: {_redact(exc)}") from None

        message = data["choices"][0]["message"]
        calls = tuple(
            ToolCall(
                id=str(raw.get("id", "")),
                name=str(raw.get("function", {}).get("name", "")),
                arguments=str(raw.get("function", {}).get("arguments", "")),
            )
            for raw in message.get("tool_calls") or ()
        )
        return ToolCallResult(
            content=message.get("content"),
            tool_calls=calls,
            model_name=self._model,
        )
