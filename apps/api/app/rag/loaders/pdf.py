"""PDF text extraction with stable one-based page references."""

from pathlib import Path

import pymupdf

from app.rag.loaders.common import normalize_text, require_blocks
from app.rag.loaders.errors import DocumentParseError, EncryptedDocumentError
from app.rag.loaders.schema import ParsedBlock, ParsedDocument


def load_pdf(source: Path) -> ParsedDocument:
    blocks: list[ParsedBlock] = []
    try:
        with pymupdf.open(source) as document:
            if document.needs_pass:
                raise EncryptedDocumentError("Password-protected PDF files are not supported.")

            page_count = document.page_count
            for page_number, page in enumerate(document, start=1):
                text = normalize_text(page.get_text("text", sort=True))
                if not text:
                    continue
                blocks.append(
                    ParsedBlock(
                        index=len(blocks),
                        kind="page",
                        text=text,
                        page_number=page_number,
                    )
                )
    except EncryptedDocumentError:
        raise
    except (OSError, pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise DocumentParseError("The PDF is invalid or could not be parsed.") from exc

    return ParsedDocument(
        source_name=source.name,
        media_type="application/pdf",
        blocks=require_blocks(blocks),
        page_count=page_count,
    )
