"""Mock Provider：不联网、确定性、零成本。

存在的理由（ADR-0001）：项目在拿到真实 API Key 之前就必须能跑通完整管线，
CI 也不应该依赖付费外部服务。Mock 保证同样的输入永远得到同样的输出，
因此可以用来断言切分、入库、检索、引用装配等环节的正确性。

它不提供任何语义能力，不能用于 M4 的效果评测。
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import AsyncIterator

_STREAM_CHUNK_SIZE = 12


class MockEmbeddingProvider:
    """用 SHA-256 派生确定性单位向量。

    相同文本 -> 相同向量；不同文本 -> 几乎必然不同的向量。
    向量已做 L2 归一化，因此余弦相似度等价于内积，与 pgvector 的行为一致。
    """

    def __init__(self, dimension: int = 1024) -> None:
        if dimension <= 0:
            raise ValueError("embedding dimension must be positive")
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return "mock-embedding"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _vector(self, text: str) -> list[float]:
        # 反复哈希以填满所需维度，保证任意维度都可复现。
        raw = bytearray()
        counter = 0
        seed = text.encode("utf-8")
        while len(raw) < self._dimension * 2:
            raw.extend(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
            counter += 1

        # 每 2 字节映射到 [-1, 1)
        values = [
            int.from_bytes(raw[i : i + 2], "big") / 32768.0 - 1.0
            for i in range(0, self._dimension * 2, 2)
        ]
        norm = math.sqrt(sum(v * v for v in values))
        if norm == 0:  # 理论上不可达，保险起见
            return [0.0] * self._dimension
        return [v / norm for v in values]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class MockLLMProvider:
    """回声式生成器：把最后一条用户消息复述出来，便于断言提示词确实送达。"""

    @property
    def model_name(self) -> str:
        return "mock-llm"

    @staticmethod
    def _answer(messages: list[dict[str, str]]) -> str:
        last_user = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        return f"[mock] 已收到问题：{last_user}"

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return self._answer(messages)

    async def stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        text = self._answer(messages)
        for i in range(0, len(text), _STREAM_CHUNK_SIZE):
            yield text[i : i + _STREAM_CHUNK_SIZE]
