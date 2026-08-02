import pytest

from app.rag.chunking import TiktokenTokenizer, chunk_blocks, chunk_document
from app.rag.loaders import load_document
from app.rag.loaders.schema import ParsedBlock, ParsedDocument


def _document(*blocks: ParsedBlock) -> ParsedDocument:
    return ParsedDocument(
        source_name="fixture.txt",
        media_type="text/plain",
        blocks=tuple(blocks),
    )


def _tokens(text: str) -> list[int]:
    return TiktokenTokenizer().encode(text)


def test_chunks_keep_page_title_and_source_order() -> None:
    document = _document(
        ParsedBlock(0, "heading", "安全制度", page_number=1, section_title="安全制度"),
        ParsedBlock(1, "paragraph", "佩戴安全帽。", page_number=1, section_title="安全制度"),
        ParsedBlock(
            2, "paragraph", "进入工地前检查设备。", page_number=1, section_title="安全制度"
        ),
        ParsedBlock(3, "heading", "请假制度", page_number=2, section_title="请假制度"),
        ParsedBlock(4, "paragraph", "周五前提交申请。", page_number=2, section_title="请假制度"),
    )

    chunks = chunk_document(document, max_tokens=100, chunk_overlap=0)

    assert [(chunk.page_number, chunk.section_title) for chunk in chunks] == [
        (1, "安全制度"),
        (2, "请假制度"),
    ]
    assert chunks[0].source_block_indices == (0, 1, 2)
    assert chunks[1].source_block_indices == (3, 4)
    assert chunks[0].index == 0 and chunks[1].index == 1
    assert "安全制度" in chunks[0].text and "请假制度" in chunks[1].text


def test_paragraphs_pack_until_the_token_limit() -> None:
    paragraphs = [f"第 {index} 段：企业安全操作流程。" for index in range(8)]
    document = _document(
        *(ParsedBlock(index, "paragraph", text) for index, text in enumerate(paragraphs))
    )

    chunks = chunk_document(document, max_tokens=20, chunk_overlap=0)

    assert len(chunks) > 1
    assert all(chunk.token_count <= 20 for chunk in chunks)
    assert all(chunk.token_count == len(_tokens(chunk.text)) for chunk in chunks)
    assert chunks[0].source_block_indices[0] == 0
    assert chunks[-1].source_block_indices[-1] == len(paragraphs) - 1


def test_exact_limit_stays_single_and_exceeding_limit_splits() -> None:
    tokenizer = TiktokenTokenizer()
    words = "policy " * 40
    exact_text = tokenizer.decode(tokenizer.encode(words)[:20])
    exact = chunk_document(
        _document(ParsedBlock(0, "paragraph", exact_text)), max_tokens=20, chunk_overlap=0
    )
    over = chunk_document(
        _document(ParsedBlock(0, "paragraph", words * 3)), max_tokens=20, chunk_overlap=0
    )

    assert len(tokenizer.encode(exact[0].text)) == 20
    assert len(exact) == 1
    assert len(over) > 1
    assert all(chunk.token_count <= 20 for chunk in over)


def test_mixed_chinese_and_english_without_spaces_is_bounded() -> None:
    text = "企业RAG安全手册Policy" * 30
    chunks = chunk_document(
        _document(ParsedBlock(0, "paragraph", text)), max_tokens=16, chunk_overlap=2
    )

    assert len(chunks) > 1
    assert all(chunk.token_count <= 16 for chunk in chunks)
    assert "企业" in "".join(chunk.text for chunk in chunks)
    assert "Policy" in "".join(chunk.text for chunk in chunks)


def test_long_block_uses_overlap() -> None:
    text = "安全流程第一步。" * 40
    chunks = chunk_document(
        _document(ParsedBlock(7, "paragraph", text)), max_tokens=24, chunk_overlap=6
    )

    assert len(chunks) > 2
    for previous, current in zip(chunks[:-1], chunks[1:], strict=True):
        previous_tail = previous.text[-12:].strip()
        assert previous_tail[-4:] in current.text
        assert current.source_block_indices == (7,)


def test_chunk_blocks_wrapper_accepts_parsed_blocks() -> None:
    chunks = chunk_blocks(
        [
            ParsedBlock(10, "paragraph", "第一段"),
            ParsedBlock(11, "paragraph", "第二段"),
        ],
        max_tokens=100,
        chunk_overlap=0,
    )

    assert len(chunks) == 1
    assert chunks[0].source_block_range == (10, 11)


def test_loader_output_can_flow_directly_into_chunking(tmp_path) -> None:
    source = tmp_path / "guide.md"
    source.write_text("# 部署\n\n先检查环境。\n\n再运行服务。", encoding="utf-8")

    parsed = load_document(source)
    chunks = chunk_document(parsed, max_tokens=100, chunk_overlap=0)

    assert len(chunks) == 1
    assert chunks[0].section_title == "部署"
    assert chunks[0].source_block_indices == (0, 1, 2)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_tokens": 0}, "max_tokens"),
        ({"max_tokens": 8, "chunk_overlap": 8}, "chunk_overlap"),
        ({"max_tokens": 8, "chunk_overlap": -1}, "chunk_overlap"),
        ({"max_tokens": 8, "chunk_overlap": 0, "min_chunk_tokens": 9}, "min_chunk_tokens"),
    ],
)
def test_rejects_invalid_chunking_parameters(kwargs: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        chunk_document(_document(ParsedBlock(0, "paragraph", "内容")), **kwargs)


def test_empty_blocks_return_no_chunks() -> None:
    document = _document(
        ParsedBlock(0, "paragraph", "   "),
        ParsedBlock(1, "paragraph", "\n\n"),
    )

    assert chunk_document(document) == ()


def test_minimum_token_filter_keeps_indices_stable() -> None:
    document = _document(
        ParsedBlock(0, "paragraph", "a", page_number=1),
        ParsedBlock(1, "paragraph", "这是一个较长的段落内容。", page_number=2),
    )

    chunks = chunk_document(document, max_tokens=100, chunk_overlap=0, min_chunk_tokens=4)

    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].source_block_indices == (1,)


def test_chunk_is_immutable() -> None:
    chunks = chunk_document(_document(ParsedBlock(0, "paragraph", "正文")))

    with pytest.raises(AttributeError):
        chunks[0].text = "changed"  # type: ignore[misc]
