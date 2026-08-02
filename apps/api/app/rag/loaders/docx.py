"""DOCX extraction preserving paragraphs, headings, and table text in document order."""

from pathlib import Path
from zipfile import BadZipFile

from docx import Document as open_docx
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError

from app.rag.loaders.common import normalize_text, require_blocks
from app.rag.loaders.errors import DocumentParseError
from app.rag.loaders.schema import ParsedBlock, ParsedDocument


def _is_heading(paragraph: Paragraph) -> bool:
    style = paragraph.style
    style_name = (style.name or "").casefold()
    style_id = (style.style_id or "").casefold()
    return style_name.startswith("heading") or style_id.startswith("heading")


def _table_text(table: Table) -> str:
    rows: list[str] = []
    for row in table.rows:
        cells = [normalize_text(cell.text).replace("\n", " ") for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def load_docx(source: Path) -> ParsedDocument:
    try:
        document = open_docx(source)
    except (OSError, BadZipFile, PackageNotFoundError, XMLSyntaxError, ValueError, KeyError) as exc:
        raise DocumentParseError("The DOCX file is invalid or could not be parsed.") from exc

    blocks: list[ParsedBlock] = []
    current_section: str | None = None
    try:
        content_items = document.iter_inner_content()
        for item in content_items:
            if isinstance(item, Paragraph):
                text = normalize_text(item.text)
                if not text:
                    continue
                is_heading = _is_heading(item)
                if is_heading:
                    current_section = text
                blocks.append(
                    ParsedBlock(
                        index=len(blocks),
                        kind="heading" if is_heading else "paragraph",
                        text=text,
                        section_title=current_section,
                    )
                )
            elif isinstance(item, Table):
                text = _table_text(item)
                if text:
                    blocks.append(
                        ParsedBlock(
                            index=len(blocks),
                            kind="table",
                            text=text,
                            section_title=current_section,
                        )
                    )
    except (KeyError, ValueError, TypeError) as exc:
        raise DocumentParseError("The DOCX content could not be extracted.") from exc

    return ParsedDocument(
        source_name=source.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        blocks=require_blocks(blocks),
    )
