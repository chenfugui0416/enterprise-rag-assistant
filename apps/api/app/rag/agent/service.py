"""Agent 编排：判断是否需要检索 → 工具调用循环 → 带引用的最终回答。

设计（ADR-0011）：
- 手写编排循环，不引入 LangGraph/AutoGen 等外部依赖，保持可测、可控、可解释。
- 只依赖 LLMProvider 协议与工具注册表，因此 Mock Provider 可以驱动完整链路。
- 循环有上限（默认 4 步）；超限不静默返回半成品，而是走显式拒答路径。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.agent.tools import ToolRegistry
from app.rag.generation.service import REFUSAL_ANSWER
from app.rag.providers.base import LLMProvider, ProviderError

DEFAULT_MAX_STEPS = 4
_MAX_GREETING_EXTRA = 6

# 纯寒暄类问题不需要检索；其余一律默认检索（宁可多检索，不可漏检索）。
_GREETING_KEYWORDS = ("你好", "您好", "hi", "hello", "在吗", "谢谢", "thanks", "thank you")

SYSTEM_PROMPT = (
    "你是企业内部知识库问答助手。规则：\n"
    "1) 涉及企业事实的问题，必须先调用 search_knowledge_base 获取原文，再依据原文回答；\n"
    "2) 回答必须标注来源（文件名、页码、标题）；\n"
    "3) 检索结果不足以回答时，明确说明资料中没有相关信息，不要编造；\n"
    "4) 纯寒暄或与知识库无关的问题可直接回答，不必检索。"
)


@dataclass(frozen=True, slots=True)
class AgentStep:
    """一次工具调用的记录。"""

    index: int
    tool_name: str
    arguments: str
    result: str


@dataclass(frozen=True, slots=True)
class AgentResult:
    question: str
    answer: str
    steps: tuple[AgentStep, ...]
    used_retrieval: bool
    refused: bool
    model_name: str


class AgentService:
    """工具调用型问答编排器。"""

    def __init__(
        self,
        llm: LLMProvider,
        registry: ToolRegistry,
        *,
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        self._llm = llm
        self._registry = registry
        self._max_steps = max_steps

    @staticmethod
    def needs_retrieval(question: str) -> bool:
        """纯寒暄短路；其余问题默认走检索。"""
        text = question.strip().lower()
        if not text:
            return False
        for keyword in _GREETING_KEYWORDS:
            if text.startswith(keyword) and len(text) <= len(keyword) + _MAX_GREETING_EXTRA:
                return False
        return True

    async def run(
        self,
        session: AsyncSession,
        knowledge_base_id: UUID,
        question: str,
        *,
        history: Sequence[dict[str, object]] | None = None,
    ) -> AgentResult:
        messages: list[dict[str, object]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        if not self.needs_retrieval(question):
            answer = await self._llm.complete(messages)  # type: ignore[arg-type]
            return AgentResult(
                question=question,
                answer=answer,
                steps=(),
                used_retrieval=False,
                refused=False,
                model_name=self._llm.model_name,
            )

        steps: list[AgentStep] = []
        tools = self._registry.specs()
        for step_index in range(1, self._max_steps + 1):
            try:
                outcome = await self._llm.complete_with_tools(messages, tools)
            except ProviderError:
                raise
            if not outcome.tool_calls:
                return AgentResult(
                    question=question,
                    answer=outcome.content or REFUSAL_ANSWER,
                    steps=tuple(steps),
                    used_retrieval=bool(steps),
                    refused=not outcome.content,
                    model_name=outcome.model_name,
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": outcome.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {"name": call.name, "arguments": call.arguments},
                        }
                        for call in outcome.tool_calls
                    ],
                }
            )
            for call in outcome.tool_calls:
                result = await self._registry.execute(
                    call.name,
                    call.arguments,
                    session=session,
                    knowledge_base_id=knowledge_base_id,
                )
                steps.append(
                    AgentStep(
                        index=step_index,
                        tool_name=call.name,
                        arguments=call.arguments,
                        result=result,
                    )
                )
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        # 步数用尽仍未给出最终回答：显式拒答，不返回半成品。
        return AgentResult(
            question=question,
            answer=REFUSAL_ANSWER,
            steps=tuple(steps),
            used_retrieval=bool(steps),
            refused=True,
            model_name=self._llm.model_name,
        )
