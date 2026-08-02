"""错误脱敏的回归测试。

背景：`_mark_failed` 曾用 `str(exc)[:500]` 直接落库，而 SQLAlchemy 的
`StatementError.__str__` 会拼接 `[SQL: ...]` 与 `[parameters: ...]`，参数即文档正文。
实测一次外键违反的 `str(exc)` 长 1241 字符且含完整正文；当时只因 SQL 段较长、
正文被挤到 500 字符之后才侥幸没落库——属偶然而非设计。

`document.error_message` 会经 API 返回给前端，因此这里把"不泄露正文"钉成断言。
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from app.rag.embeddings.service import safe_error_detail

SECRET = "员工年假15天报销上限8000元这是不该出现在错误信息里的正文"


def _statement_error(exc_type: type) -> Exception:
    """复刻真实场景：SQLAlchemy 把 SQL 与绑定参数塞进异常字符串。"""

    return exc_type(
        "INSERT INTO document_chunks (id, content, embedding) VALUES (%(id)s, %(content)s)",
        {"content": SECRET},
        Exception('duplicate key value violates unique constraint "uq_chunk"'),
    )


@pytest.mark.parametrize("exc_type", [IntegrityError, OperationalError])
def test_sqlalchemy_errors_never_leak_document_content(exc_type: type) -> None:
    exc = _statement_error(exc_type)

    # 前提校验：原始异常确实包含正文，否则这条测试就失去意义
    assert SECRET in str(exc)

    detail = safe_error_detail(exc)

    assert SECRET not in detail
    assert "[SQL:" not in detail
    assert "[parameters:" not in detail
    # 仍需保留可诊断信息
    assert exc_type.__name__ in detail
    assert "duplicate key" in detail


def test_redacted_detail_is_single_line_and_bounded() -> None:
    exc = _statement_error(IntegrityError)
    detail = safe_error_detail(exc)

    assert "\n" not in detail
    assert len(detail) <= 260


def test_plain_exception_keeps_first_line_only() -> None:
    exc = ValueError(f"配置缺失\n第二行不应出现\n{SECRET}")

    detail = safe_error_detail(exc)

    assert detail == "ValueError: 配置缺失"
    assert SECRET not in detail


def test_exception_without_message_falls_back_to_type_name() -> None:
    detail = safe_error_detail(RuntimeError())

    assert detail == "RuntimeError: RuntimeError"
