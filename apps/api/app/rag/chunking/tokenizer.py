"""Tokenization helpers used by the deterministic chunking service."""

from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

import tiktoken


class Tokenizer(Protocol):
    """Small protocol that keeps chunking testable without a model client."""

    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: Sequence[int]) -> str: ...


class TiktokenTokenizer:
    """Adapter around a tiktoken encoding selected by name."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self.encoding_name = encoding_name
        self._encoding = _get_encoding(encoding_name)

    def encode(self, text: str) -> list[int]:
        return self._encoding.encode(text, disallowed_special=())

    def decode(self, tokens: Sequence[int]) -> str:
        return self._encoding.decode(list(tokens))


@lru_cache(maxsize=8)
def _get_encoding(encoding_name: str) -> tiktoken.Encoding:
    try:
        return tiktoken.get_encoding(encoding_name)
    except ValueError as exc:
        raise ValueError(f"Unknown tiktoken encoding: {encoding_name!r}.") from exc
