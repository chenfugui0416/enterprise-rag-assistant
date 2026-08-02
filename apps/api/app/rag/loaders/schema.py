"""Format-neutral document parsing results consumed by the chunking stage."""

from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["page", "heading", "paragraph", "table", "code", "text"]


@dataclass(frozen=True, slots=True)
class ParsedBlock:
    index: int
    kind: BlockKind
    text: str
    page_number: int | None = None
    section_title: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    source_name: str
    media_type: str
    blocks: tuple[ParsedBlock, ...]
    page_count: int | None = None
    encoding: str | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks)

    @property
    def character_count(self) -> int:
        return sum(len(block.text) for block in self.blocks)
