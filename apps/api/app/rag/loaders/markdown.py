"""CommonMark parser that extracts visible block text and heading context."""

from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.token import Token

from app.rag.loaders.common import normalize_text, require_blocks
from app.rag.loaders.errors import DocumentParseError
from app.rag.loaders.schema import ParsedBlock, ParsedDocument


def _inline_text(token: Token) -> str:
    if not token.children:
        return normalize_text(token.content)

    fragments: list[str] = []
    for child in token.children:
        if child.type in {"text", "code_inline"}:
            fragments.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            fragments.append("\n")
        elif child.type == "image":
            fragments.append(child.content)
    return normalize_text("".join(fragments))


def load_markdown(source: Path) -> ParsedDocument:
    try:
        raw_text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise DocumentParseError("Markdown files must use UTF-8 encoding.") from exc

    try:
        tokens = MarkdownIt("commonmark", {"html": False}).parse(raw_text)
    except (RuntimeError, ValueError) as exc:
        raise DocumentParseError("The Markdown file could not be parsed.") from exc

    blocks: list[ParsedBlock] = []
    current_section: str | None = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and index + 1 < len(tokens):
            heading = _inline_text(tokens[index + 1])
            if heading:
                current_section = heading
                blocks.append(
                    ParsedBlock(
                        index=len(blocks),
                        kind="heading",
                        text=heading,
                        section_title=heading,
                    )
                )
        elif token.type == "inline" and (index == 0 or tokens[index - 1].type != "heading_open"):
            text = _inline_text(token)
            if text:
                blocks.append(
                    ParsedBlock(
                        index=len(blocks),
                        kind="paragraph",
                        text=text,
                        section_title=current_section,
                    )
                )
        elif token.type in {"fence", "code_block"}:
            text = normalize_text(token.content)
            if text:
                blocks.append(
                    ParsedBlock(
                        index=len(blocks),
                        kind="code",
                        text=text,
                        section_title=current_section,
                    )
                )

    return ParsedDocument(
        source_name=source.name,
        media_type="text/markdown",
        blocks=require_blocks(blocks),
        encoding="utf-8",
    )
