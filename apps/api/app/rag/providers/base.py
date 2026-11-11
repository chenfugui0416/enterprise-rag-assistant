"""Provider 抽象层。

见 docs/DECISIONS.md ADR-0001：业务代码只依赖这里的协议，不依赖任何具体
模型厂商。切换厂商只改环境变量，不改调用方。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """把文本转成向量。"""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量编码。返回顺序与入参一一对应。"""
        ...


@dataclass(frozen=True, slots=True)
class ToolCall:
    """模型请求调用一个工具；arguments 是原始 JSON 字符串。"""

    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class ToolCallResult:
    """带工具的一次生成结果：要么给出最终回答，要么请求调用工具。"""

    content: str | None
    tool_calls: tuple[ToolCall, ...]
    model_name: str


@runtime_checkable
class LLMProvider(Protocol):
    """生成回答。"""

    @property
    def model_name(self) -> str: ...

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """一次性返回完整回答。"""
        ...

    def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """流式返回增量文本片段。"""
        ...

    async def complete_with_tools(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ToolCallResult:
        """带工具定义的一次生成。

        不提供工具调用能力的实现应抛 ProviderError（见 ADR-0011）。
        """
        ...


class ProviderError(RuntimeError):
    """Provider 调用失败。

    注意：向上抛出时不得携带 API Key、完整请求头或文档正文。
    """
