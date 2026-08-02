"""Public document parsing API."""

from app.rag.loaders.common import DEFAULT_MAX_FILE_SIZE
from app.rag.loaders.errors import (
    DocumentParseError,
    DocumentTooLargeError,
    EmptyDocumentError,
    EncryptedDocumentError,
    UnsupportedDocumentTypeError,
)
from app.rag.loaders.schema import BlockKind, ParsedBlock, ParsedDocument
from app.rag.loaders.service import LOADERS, load_document

__all__ = [
    "DEFAULT_MAX_FILE_SIZE",
    "LOADERS",
    "BlockKind",
    "DocumentParseError",
    "DocumentTooLargeError",
    "EmptyDocumentError",
    "EncryptedDocumentError",
    "ParsedBlock",
    "ParsedDocument",
    "UnsupportedDocumentTypeError",
    "load_document",
]
