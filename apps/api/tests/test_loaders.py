from pathlib import Path

import pymupdf
import pytest
from docx import Document as create_docx

from app.rag.loaders import (
    DocumentParseError,
    DocumentTooLargeError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
    load_document,
)


def test_load_pdf_preserves_one_based_page_numbers(tmp_path: Path) -> None:
    source = tmp_path / "manual.pdf"
    document = pymupdf.open()
    first_page = document.new_page()
    first_page.insert_text((72, 72), "Safety policy overview")
    second_page = document.new_page()
    second_page.insert_text((72, 72), "Emergency contact procedure")
    document.save(source)
    document.close()

    parsed = load_document(source)

    assert parsed.media_type == "application/pdf"
    assert parsed.page_count == 2
    assert [block.page_number for block in parsed.blocks] == [1, 2]
    assert "Safety policy overview" in parsed.blocks[0].text
    assert "Emergency contact procedure" in parsed.blocks[1].text


def test_load_docx_preserves_heading_context_and_tables(tmp_path: Path) -> None:
    source = tmp_path / "handbook.docx"
    document = create_docx()
    document.add_heading("Leave policy", level=1)
    document.add_paragraph("Employees submit leave requests before Friday.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Type"
    table.cell(0, 1).text = "Days"
    table.cell(1, 0).text = "Annual"
    table.cell(1, 1).text = "10"
    document.save(source)

    parsed = load_document(source)

    assert [block.kind for block in parsed.blocks] == ["heading", "paragraph", "table"]
    assert all(block.section_title == "Leave policy" for block in parsed.blocks)
    assert parsed.blocks[2].text == "Type | Days\nAnnual | 10"
    assert parsed.page_count is None


def test_load_markdown_extracts_visible_text_and_code(tmp_path: Path) -> None:
    source = tmp_path / "guide.md"
    source.write_text(
        "# Deployment\n\nUse **Docker Compose** with [the guide](https://example.test).\n\n"
        "- Start the database\n- Run migrations\n\n```bash\nmake up\n```\n",
        encoding="utf-8",
    )

    parsed = load_document(source)

    assert parsed.blocks[0].kind == "heading"
    assert parsed.blocks[0].text == "Deployment"
    assert "Use Docker Compose with the guide." in parsed.text
    assert "Start the database" in parsed.text
    assert parsed.blocks[-1].kind == "code"
    assert parsed.blocks[-1].text == "make up"
    assert all(block.section_title == "Deployment" for block in parsed.blocks)


def test_load_text_detects_gb18030_and_splits_paragraphs(tmp_path: Path) -> None:
    source = tmp_path / "policy.txt"
    source.write_bytes("第一段：员工手册。\n\n第二段：安全制度。".encode("gb18030"))

    parsed = load_document(source)

    assert parsed.media_type == "text/plain"
    assert parsed.encoding is not None
    assert parsed.encoding == "gb18030"
    assert [block.text for block in parsed.blocks] == [
        "第一段：员工手册。",
        "第二段：安全制度。",
    ]


def test_load_text_accepts_utf8_bom(tmp_path: Path) -> None:
    source = tmp_path / "utf8.txt"
    source.write_bytes(b"\xef\xbb\xbfPolicy title\n\nPolicy body")

    parsed = load_document(source)

    assert parsed.encoding == "utf-8"
    assert parsed.blocks[0].text == "Policy title"


@pytest.mark.parametrize("suffix", [".csv", ".doc", ".exe"])
def test_rejects_unsupported_extensions(tmp_path: Path, suffix: str) -> None:
    source = tmp_path / f"source{suffix}"
    source.write_text("content", encoding="utf-8")

    with pytest.raises(UnsupportedDocumentTypeError):
        load_document(source)


def test_rejects_missing_empty_binary_and_oversized_files(tmp_path: Path) -> None:
    with pytest.raises(DocumentParseError):
        load_document(tmp_path / "missing.txt")

    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    with pytest.raises(EmptyDocumentError):
        load_document(empty)

    binary = tmp_path / "binary.txt"
    binary.write_bytes(b"text\x00binary")
    with pytest.raises(DocumentParseError):
        load_document(binary)

    oversized = tmp_path / "large.txt"
    oversized.write_text("12345", encoding="utf-8")
    with pytest.raises(DocumentTooLargeError):
        load_document(oversized, max_bytes=4)


def test_rejects_corrupt_pdf_without_exposing_the_path(tmp_path: Path) -> None:
    source = tmp_path / "private-client-name.pdf"
    source.write_bytes(b"not a pdf")

    with pytest.raises(DocumentParseError) as error:
        load_document(source)

    assert str(source) not in str(error.value)


def test_rejects_corrupt_docx_with_a_public_parse_error(tmp_path: Path) -> None:
    source = tmp_path / "broken.docx"
    source.write_bytes(b"not an office package")

    with pytest.raises(DocumentParseError, match="DOCX"):
        load_document(source)
