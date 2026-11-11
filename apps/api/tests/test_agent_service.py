"""ADR-0011 Agent 编排测试：检索分支、工具循环、步数上限拒答、寒暄短路。

用 Mock Provider 驱动完整链路——不联网、零成本，且行为确定可断言。
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.rag.agent import AgentService
from app.rag.generation import REFUSAL_ANSWER
from app.rag.providers.base import ToolCall, ToolCallResult
from app.rag.providers.mock import MockLLMProvider


class FakeRegistry:
    """只记录调用、返回固定 JSON，不接触数据库。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def specs(self) -> list[dict[str, object]]:
        return [{"type": "function", "function": {"name": "search_knowledge_base"}}]

    async def execute(self, name: str, arguments: str, *, session, knowledge_base_id) -> str:
        self.calls.append((name, arguments))
        return json.dumps(
            {"count": 1, "results": [{"citation": "手册.pdf · 第 3 页"}]}, ensure_ascii=False
        )


class LoopingLLMProvider:
    """永远请求工具调用，用于验证步数上限的拒答路径。"""

    @property
    def model_name(self) -> str:
        return "looping-llm"

    async def complete(self, messages: list[dict[str, object]]) -> str:
        return "unused"

    async def complete_with_tools(self, messages, tools) -> ToolCallResult:
        return ToolCallResult(
            content=None,
            tool_calls=(ToolCall("call-x", "search_knowledge_base", '{"query": "循环"}'),),
            model_name=self.model_name,
        )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("你好", False),
        ("您好，请问在吗", False),
        ("Hello", False),
        ("谢谢！", False),
        ("公司的报销标准是多少？", True),
        ("请总结一下这份安全手册的要点", True),
    ],
)
def test_needs_retrieval_heuristic(question: str, expected: bool) -> None:
    assert AgentService.needs_retrieval(question) is expected


async def test_agent_runs_tool_then_answers() -> None:
    registry = FakeRegistry()
    service = AgentService(MockLLMProvider(), registry)  # type: ignore[arg-type]

    result = await service.run(None, uuid4(), "公司的报销标准是多少？")  # type: ignore[arg-type]

    assert result.used_retrieval is True
    assert result.refused is False
    assert len(result.steps) == 1
    assert result.steps[0].tool_name == "search_knowledge_base"
    assert "报销标准" in result.steps[0].arguments
    assert result.answer.startswith("[mock-agent]")
    assert len(registry.calls) == 1


async def test_greeting_short_circuits_retrieval() -> None:
    registry = FakeRegistry()
    service = AgentService(MockLLMProvider(), registry)  # type: ignore[arg-type]

    result = await service.run(None, uuid4(), "你好")  # type: ignore[arg-type]

    assert result.used_retrieval is False
    assert result.steps == ()
    assert registry.calls == []
    assert "你好" in result.answer


async def test_max_steps_exhaustion_refuses_instead_of_returning_half_answer() -> None:
    service = AgentService(LoopingLLMProvider(), FakeRegistry(), max_steps=2)  # type: ignore[arg-type]

    result = await service.run(None, uuid4(), "这是需要检索的问题")  # type: ignore[arg-type]

    assert result.refused is True
    assert result.answer == REFUSAL_ANSWER
    assert len(result.steps) == 2


def test_agent_rejects_invalid_max_steps() -> None:
    with pytest.raises(ValueError):
        AgentService(MockLLMProvider(), FakeRegistry(), max_steps=0)  # type: ignore[arg-type]
