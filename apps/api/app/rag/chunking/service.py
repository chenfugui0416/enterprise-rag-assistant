"""Structure-aware, token-bounded document chunking."""

import re
from collections.abc import Iterable, Sequence

from app.rag.chunking.schema import Chunk, ChunkingConfig
from app.rag.chunking.tokenizer import TiktokenTokenizer, Tokenizer
from app.rag.loaders.schema import ParsedBlock, ParsedDocument

_SENTENCE_PATTERN = re.compile(r".+?(?:[。！？!?；;]|[.!?](?=\s|$)|\n|$)", re.DOTALL)
_SEPARATOR = "\n\n"


class _Piece:
    __slots__ = ("block_index", "page_number", "section_title", "tokens", "continuation")

    def __init__(
        self,
        *,
        block_index: int,
        page_number: int | None,
        section_title: str | None,
        tokens: list[int],
        continuation: bool,
    ) -> None:
        self.block_index = block_index
        self.page_number = page_number
        self.section_title = section_title
        self.tokens = tokens
        self.continuation = continuation


def _normalise_block_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _token_windows(tokens: list[int], max_tokens: int, overlap: int) -> list[list[int]]:
    step = max_tokens - overlap
    return [tokens[start : start + max_tokens] for start in range(0, len(tokens), step)]


def _split_long_text(
    text: str,
    tokenizer: Tokenizer,
    max_tokens: int,
) -> list[tuple[list[int], bool]]:
    """Prefer sentence/line boundaries, then fall back to exact token windows."""

    token_ids = tokenizer.encode(text)
    if len(token_ids) <= max_tokens:
        return [(token_ids, False)]

    segments = [
        match.group(0).strip()
        for match in _SENTENCE_PATTERN.finditer(text)
        if match.group(0).strip()
    ]
    if len(segments) <= 1:
        segments = [line.strip() for line in text.splitlines() if line.strip()]
    if len(segments) <= 1:
        return [(token_ids, False)]

    pieces: list[tuple[list[int], bool]] = []
    current: list[int] = []
    separator_tokens = tokenizer.encode(_SEPARATOR)
    for segment in segments:
        segment_tokens = tokenizer.encode(segment)
        if len(segment_tokens) > max_tokens:
            if current:
                pieces.append((current, len(pieces) > 0))
                current = []
            pieces.append((segment_tokens, len(pieces) > 0))
        elif current and len(current) + len(separator_tokens) + len(segment_tokens) > max_tokens:
            pieces.append((current, len(pieces) > 0))
            current = segment_tokens
        elif current:
            current.extend(separator_tokens)
            current.extend(segment_tokens)
        else:
            current = segment_tokens
    if current:
        pieces.append((current, len(pieces) > 0))
    return pieces


def _iter_groups(
    blocks: Iterable[ParsedBlock],
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> Iterable[tuple[tuple[int | None, str | None], list[_Piece]]]:
    current_section: str | None = None
    group_key: tuple[int | None, str | None] | None = None
    group: list[_Piece] = []

    for block in blocks:
        text = _normalise_block_text(block.text)
        if not text:
            continue
        if block.kind == "heading":
            current_section = text
        elif block.section_title is not None:
            current_section = block.section_title
        key = block.page_number, current_section
        if group_key is not None and key != group_key:
            yield group_key, group
            group = []
        group_key = key
        for tokens, continuation in _split_long_text(text, tokenizer, config.max_tokens):
            group.append(
                _Piece(
                    block_index=block.index,
                    page_number=block.page_number,
                    section_title=current_section,
                    tokens=tokens,
                    continuation=continuation,
                )
            )
    if group_key is not None and group:
        yield group_key, group


def _group_windows(
    pieces: Sequence[_Piece],
    config: ChunkingConfig,
    tokenizer: Tokenizer,
) -> list[Chunk]:
    tokens: list[int] = []
    sources: list[int] = []
    for piece in pieces:
        if tokens and not piece.continuation:
            separator = tokenizer.encode(_SEPARATOR)
            tokens.extend(separator)
            sources.extend([piece.block_index] * len(separator))
        tokens.extend(piece.tokens)
        sources.extend([piece.block_index] * len(piece.tokens))

    chunks: list[Chunk] = []
    step = config.max_tokens - config.chunk_overlap
    for start in range(0, len(tokens), step):
        end = min(start + config.max_tokens, len(tokens))
        raw_text = tokenizer.decode(tokens[start:end]).strip()
        if not raw_text:
            continue
        text = raw_text
        token_count = len(tokenizer.encode(text))
        chunk_sources = tuple(dict.fromkeys(sources[start:end]))
        chunks.append(
            Chunk(
                index=-1,
                text=text,
                token_count=token_count,
                page_number=pieces[0].page_number,
                section_title=pieces[0].section_title,
                source_block_indices=chunk_sources,
            )
        )
        if end == len(tokens):
            break
    return chunks


def chunk_document(
    document: ParsedDocument,
    *,
    max_tokens: int = 512,
    chunk_overlap: int = 0,
    min_chunk_tokens: int = 1,
    encoding_name: str = "cl100k_base",
    tokenizer: Tokenizer | None = None,
) -> tuple[Chunk, ...]:
    """Split a parsed document while retaining semantic and source metadata."""

    config = ChunkingConfig(
        max_tokens=max_tokens,
        chunk_overlap=chunk_overlap,
        min_chunk_tokens=min_chunk_tokens,
        encoding_name=encoding_name,
    )
    active_tokenizer = tokenizer or TiktokenTokenizer(config.encoding_name)
    chunks: list[Chunk] = []
    for _, pieces in _iter_groups(document.blocks, config, active_tokenizer):
        chunks.extend(_group_windows(pieces, config, active_tokenizer))

    filtered = [chunk for chunk in chunks if chunk.token_count >= config.min_chunk_tokens]
    return tuple(
        Chunk(
            index=index,
            text=chunk.text,
            token_count=chunk.token_count,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            source_block_indices=chunk.source_block_indices,
        )
        for index, chunk in enumerate(filtered)
    )


def chunk_blocks(
    blocks: Sequence[ParsedBlock],
    **kwargs: object,
) -> tuple[Chunk, ...]:
    """Convenience wrapper for callers that already have parsed blocks."""

    document = ParsedDocument(
        source_name="<blocks>",
        media_type="application/octet-stream",
        blocks=tuple(blocks),
    )
    return chunk_document(document, **kwargs)


split_document = chunk_document
