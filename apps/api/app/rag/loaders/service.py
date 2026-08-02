"""Single entry point for validated, format-specific document parsing."""

from collections.abc import Callable
from pathlib import Path

from app.rag.loaders.common import DEFAULT_MAX_FILE_SIZE, validate_source
from app.rag.loaders.docx import load_docx
from app.rag.loaders.errors import UnsupportedDocumentTypeError
from app.rag.loaders.markdown import load_markdown
from app.rag.loaders.pdf import load_pdf
from app.rag.loaders.schema import ParsedDocument
from app.rag.loaders.text import load_text

Loader = Callable[[Path], ParsedDocument]

LOADERS: dict[str, Loader] = {
    ".docx": load_docx,
    ".markdown": load_markdown,
    ".md": load_markdown,
    ".pdf": load_pdf,
    ".txt": load_text,
}


def load_document(path: str | Path, *, max_bytes: int = DEFAULT_MAX_FILE_SIZE) -> ParsedDocument:
    source = validate_source(path, max_bytes=max_bytes)
    loader = LOADERS.get(source.suffix.casefold())
    if loader is None:
        supported = ", ".join(sorted(LOADERS))
        raise UnsupportedDocumentTypeError(
            f"Unsupported document type. Supported extensions: {supported}."
        )
    return loader(source)
