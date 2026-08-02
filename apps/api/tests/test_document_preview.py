import io

import pytest
from fastapi.testclient import TestClient

from app.api.routes import document_preview


def test_preview_text_returns_blocks_chunks_and_statistics(client: TestClient) -> None:
    response = client.post(
        "/documents/preview?max_tokens=32&chunk_overlap=4",
        files={"file": ("员工制度.txt", "第一章 年假\n\n员工每年享有十天年假。".encode())},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "员工制度.txt"
    assert body["media_type"] == "text/plain"
    assert body["block_count"] == 2
    assert body["chunk_count"] == 1
    assert body["character_count"] > 0
    assert body["total_tokens"] == body["chunks"][0]["token_count"]
    assert body["config"] == {"max_tokens": 32, "chunk_overlap": 4}
    assert body["blocks"][0]["index"] == 0
    assert body["chunks"][0]["source_block_indices"] == [0, 1]


def test_preview_markdown_preserves_heading_context(client: TestClient) -> None:
    response = client.post(
        "/documents/preview?max_tokens=64&chunk_overlap=8",
        files={"file": ("handbook.md", b"# Leave policy\n\nSubmit requests on Friday.")},
    )

    assert response.status_code == 200
    body = response.json()
    assert [block["kind"] for block in body["blocks"]] == ["heading", "paragraph"]
    assert body["chunks"][0]["section_title"] == "Leave policy"


@pytest.mark.parametrize("filename", ["data.csv", "legacy.doc", "program.exe"])
def test_preview_rejects_unsupported_types(client: TestClient, filename: str) -> None:
    response = client.post("/documents/preview", files={"file": (filename, b"content")})

    assert response.status_code == 415
    assert response.json()["detail"] == "仅支持 PDF、DOCX、Markdown 和 TXT 文档。"


def test_preview_rejects_invalid_overlap(client: TestClient) -> None:
    response = client.post(
        "/documents/preview?max_tokens=32&chunk_overlap=32",
        files={"file": ("policy.txt", b"content")},
    )

    assert response.status_code == 400
    assert "重叠" in response.json()["detail"]


def test_preview_rejects_corrupt_document(client: TestClient) -> None:
    response = client.post(
        "/documents/preview",
        files={"file": ("private-customer.pdf", b"not a pdf")},
    )

    assert response.status_code == 422
    assert "private-customer" not in response.text


def test_preview_enforces_streaming_size_limit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(document_preview, "MAX_PREVIEW_BYTES", 4)

    response = client.post(
        "/documents/preview",
        files={"file": ("policy.txt", io.BytesIO(b"12345"))},
    )

    assert response.status_code == 413
