"""ADR-0011 Agent 工具层测试：算术安全求值、工具 Schema、参数校验。

工具层不依赖任何外部服务，因此这些断言在 CI 上零成本、确定性通过。
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.rag.agent.tools import ToolError, ToolRegistry, safe_eval_arithmetic


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1+2*3", 7.0),
        ("(120-95)/120", 0.20833333333333334),
        ("2**10", 1024.0),
        ("-3 + 1.5", -1.5),
        ("10 // 3", 3.0),
    ],
)
def test_safe_eval_arithmetic_allows_plain_math(expression: str, expected: float) -> None:
    assert safe_eval_arithmetic(expression) == pytest.approx(expected)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('ls')",
        "open('/etc/passwd')",
        "a + b",
        "[1,2][0]",
        "1/0",
        "",
        "1" * 300,
    ],
)
def test_safe_eval_arithmetic_rejects_everything_else(expression: str) -> None:
    with pytest.raises(ToolError):
        safe_eval_arithmetic(expression)


def test_specs_expose_three_tools_in_openai_format() -> None:
    registry = ToolRegistry(retrieval=None)  # type: ignore[arg-type]
    specs = registry.specs()
    assert [s["function"]["name"] for s in specs] == [  # type: ignore[index]
        "search_knowledge_base",
        "get_document_meta",
        "calculator",
    ]
    for spec in specs:
        assert spec["type"] == "function"
        function = spec["function"]  # type: ignore[index]
        assert function["description"]
        assert function["parameters"]["type"] == "object"
        assert function["parameters"]["required"]
    assert registry.tool_names == ("search_knowledge_base", "get_document_meta", "calculator")


async def test_calculator_executes_without_database() -> None:
    registry = ToolRegistry(retrieval=None)  # type: ignore[arg-type]
    raw = await registry.execute(
        "calculator",
        json.dumps({"expression": "(120-95)/120"}),
        session=None,
        knowledge_base_id=uuid4(),
    )
    assert json.loads(raw)["result"] == pytest.approx(0.20833333333333334)


async def test_execute_reports_errors_as_readable_payload() -> None:
    registry = ToolRegistry(retrieval=None)  # type: ignore[arg-type]
    cases = [
        ("calculator", "{not json}"),
        ("calculator", json.dumps({"expression": "1/0"})),
        ("unknown_tool", "{}"),
        ("search_knowledge_base", json.dumps({"query": "   "})),
        ("search_knowledge_base", json.dumps({"query": "x", "top_k": 99})),
        ("get_document_meta", json.dumps({"document_id": "not-a-uuid"})),
    ]
    for name, arguments in cases:
        payload = json.loads(
            await registry.execute(name, arguments, session=None, knowledge_base_id=uuid4())
        )
        assert "error" in payload, (name, arguments)
