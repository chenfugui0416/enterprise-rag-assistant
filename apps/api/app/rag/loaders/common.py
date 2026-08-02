"""Shared validation and normalization helpers for document loaders."""

from pathlib import Path

from app.rag.loaders.errors import (
    DocumentParseError,
    DocumentTooLargeError,
    EmptyDocumentError,
)
from app.rag.loaders.schema import ParsedBlock

DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024


def validate_source(path: str | Path, *, max_bytes: int) -> Path:
    source = Path(path)
    if not source.is_file():
        raise DocumentParseError("The document file does not exist or is not a regular file.")
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero.")
    if source.stat().st_size > max_bytes:
        raise DocumentTooLargeError(f"The document exceeds the {max_bytes}-byte limit.")
    return source


def normalize_text(value: str) -> str:
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(line.rstrip() for line in lines).strip()


def require_blocks(blocks: list[ParsedBlock]) -> tuple[ParsedBlock, ...]:
    if not blocks:
        raise EmptyDocumentError("The document contains no extractable text.")
    return tuple(blocks)
