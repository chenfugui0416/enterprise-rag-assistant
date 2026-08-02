"""Plain-text loader with deterministic charset detection and paragraph boundaries."""

import re
from pathlib import Path

from charset_normalizer import from_bytes

from app.rag.loaders.common import normalize_text, require_blocks
from app.rag.loaders.errors import DocumentParseError
from app.rag.loaders.schema import ParsedBlock, ParsedDocument


def _decode_text(raw: bytes) -> tuple[str, str]:
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        pass

    matches = list(from_bytes(raw))
    if not matches:
        raise DocumentParseError("The text encoding could not be detected.")

    # Short CJK text is ambiguous: charset-normalizer can rank CP949 above GB18030
    # even when both are valid candidates. The product explicitly supports Chinese
    # files, so prefer Chinese encodings among the detector's candidates.
    for preferred in ("gb18030", "big5"):
        for match in matches:
            if match.encoding.casefold() == preferred:
                return str(match), match.encoding

    return str(matches[0]), matches[0].encoding


def load_text(source: Path) -> ParsedDocument:
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise DocumentParseError("The text file could not be read.") from exc

    if b"\x00" in raw:
        raise DocumentParseError("The text file appears to contain binary data.")

    decoded, encoding = _decode_text(raw)
    text = normalize_text(decoded)
    paragraphs = [normalize_text(value) for value in re.split(r"\n\s*\n", text)]
    blocks = [
        ParsedBlock(index=index, kind="text", text=value)
        for index, value in enumerate(paragraph for paragraph in paragraphs if paragraph)
    ]
    return ParsedDocument(
        source_name=source.name,
        media_type="text/plain",
        blocks=require_blocks(blocks),
        encoding=encoding,
    )
