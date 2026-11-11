"""Agent 工具层：把检索、文档元数据与计算器封装成模型可调用的工具。

设计约束（ADR-0011）：工具只依赖 Provider / Service 抽象，不依赖任何具体模型厂商；
工具入参一律先校验再执行，任何异常都转成可读的工具错误信息返回给模型，而不是抛出。
"""

from __future__ import annotations

import ast
import json
import operator
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.rag.retrieval import VectorSearchService

MAX_EXPRESSION_LENGTH = 200
MAX_SEARCH_TOP_K = 10

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class ToolError(ValueError):
    """工具入参不合法或执行失败。"""


def safe_eval_arithmetic(expression: str) -> float:
    """只允许数字常量、括号与 + - * / // % ** 的算术表达式。

    不使用 eval：先 ast.parse，再对语法树白名单求值。
    """
    if not expression or len(expression) > MAX_EXPRESSION_LENGTH:
        raise ToolError("表达式为空或过长")
    try:
        node = ast.parse(expression, mode="eval")
    except SyntaxError:
        raise ToolError("表达式无法解析") from None
    return float(_eval_node(node.body))


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError("只允许数字常量")
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval_node(node.left), _eval_node(node.right)
        try:
            return float(_BIN_OPS[type(node.op)](left, right))
        except ZeroDivisionError:
            raise ToolError("除数不能为 0") from None
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return float(_UNARY_OPS[type(node.op)](_eval_node(node.operand)))
    raise ToolError("表达式含不允许的语法")


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, object]

    def as_openai_tool(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="search_knowledge_base",
        description="在企业知识库中检索与问题相关的原文片段，返回带来源标注（文件名/页码/标题）的片段列表。回答事实性问题前应先调用它。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索用的自然语言问题或关键词"},
                "top_k": {
                    "type": "integer",
                    "description": f"返回片段数量，默认 5，范围 1-{MAX_SEARCH_TOP_K}",
                    "minimum": 1,
                    "maximum": MAX_SEARCH_TOP_K,
                },
            },
            "required": ["query"],
        },
    ),
    ToolSpec(
        name="get_document_meta",
        description="查询某份文档的元数据（文件名、类型、大小、页数、处理状态），用于确认资料是否已被正确收录。",
        parameters={
            "type": "object",
            "properties": {"document_id": {"type": "string", "description": "文档 UUID"}},
            "required": ["document_id"],
        },
    ),
    ToolSpec(
        name="calculator",
        description="执行纯算术计算（支持 + - * / // % ** 与括号），用于回答需要数值计算的问题。",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "算术表达式，例如 (120-95)/120"}
            },
            "required": ["expression"],
        },
    ),
)


class ToolRegistry:
    """工具注册表：向模型暴露 JSON Schema，并按名执行。"""

    def __init__(self, retrieval: VectorSearchService) -> None:
        self._retrieval = retrieval

    def specs(self) -> list[dict[str, object]]:
        return [spec.as_openai_tool() for spec in SPECS]

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in SPECS)

    async def execute(
        self,
        name: str,
        arguments: str,
        *,
        session: AsyncSession,
        knowledge_base_id: UUID,
    ) -> str:
        """执行工具，返回给模型看的字符串结果。任何失败都返回可读错误，不抛异常。"""
        try:
            payload = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return self._error("工具参数不是合法 JSON")
        if not isinstance(payload, dict):
            return self._error("工具参数必须是 JSON 对象")

        try:
            if name == "search_knowledge_base":
                return await self._search(payload, session, knowledge_base_id)
            if name == "get_document_meta":
                return await self._document_meta(payload, session)
            if name == "calculator":
                return self._calculate(payload)
        except ToolError as exc:
            return self._error(str(exc))
        return self._error(f"未知工具：{name}")

    @staticmethod
    def _error(message: str) -> str:
        return json.dumps({"error": message}, ensure_ascii=False)

    async def _search(
        self, payload: dict[str, object], session: AsyncSession, knowledge_base_id: UUID
    ) -> str:
        query = str(payload.get("query", "")).strip()
        if not query:
            raise ToolError("query 不能为空")
        top_k = payload.get("top_k", 5)
        if not isinstance(top_k, int) or not 1 <= top_k <= MAX_SEARCH_TOP_K:
            raise ToolError(f"top_k 必须是 1-{MAX_SEARCH_TOP_K} 的整数")
        results = await self._retrieval.search(session, knowledge_base_id, query, top_k=top_k)
        return json.dumps(
            {
                "count": len(results),
                "results": [
                    {
                        "citation": r.citation_label,
                        "score": round(r.score, 4),
                        "content": r.content,
                    }
                    for r in results
                ],
            },
            ensure_ascii=False,
        )

    async def _document_meta(self, payload: dict[str, object], session: AsyncSession) -> str:
        raw_id = str(payload.get("document_id", "")).strip()
        try:
            document_id = UUID(raw_id)
        except (ValueError, AttributeError):
            raise ToolError("document_id 不是合法 UUID") from None
        document = await session.get(Document, document_id)
        if document is None:
            raise ToolError("未找到该文档")
        return json.dumps(
            {
                "filename": document.filename,
                "mime_type": document.mime_type,
                "size_bytes": document.size_bytes,
                "page_count": document.page_count,
                "status": getattr(document.status, "value", str(document.status)),
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _calculate(payload: dict[str, object]) -> str:
        expression = str(payload.get("expression", "")).strip()
        return json.dumps({"result": safe_eval_arithmetic(expression)}, ensure_ascii=False)
