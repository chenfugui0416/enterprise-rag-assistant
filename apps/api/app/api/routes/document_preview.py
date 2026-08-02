"""Upload endpoint that exposes parsing and chunking results without persistence."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.rag.chunking import chunk_document
from app.rag.loaders import (
    DEFAULT_MAX_FILE_SIZE,
    LOADERS,
    DocumentParseError,
    DocumentTooLargeError,
    UnsupportedDocumentTypeError,
    load_document,
)
from app.schemas.document_preview import (
    ChunkingConfigResponse,
    ChunkResponse,
    DocumentPreviewResponse,
    ParsedBlockResponse,
)

router = APIRouter(prefix="/documents", tags=["documents"])

_COPY_BUFFER_SIZE = 1024 * 1024
MAX_PREVIEW_BYTES = DEFAULT_MAX_FILE_SIZE


async def _save_upload(upload: UploadFile, destination: Path) -> int:
    size = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(_COPY_BUFFER_SIZE):
            size += len(chunk)
            if size > MAX_PREVIEW_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"文件不能超过 {MAX_PREVIEW_BYTES // (1024 * 1024)} MiB。",
                )
            output.write(chunk)
    return size


@router.post(
    "/preview",
    response_model=DocumentPreviewResponse,
    summary="解析文档并预览结构化切分结果",
)
async def preview_document(
    file: Annotated[UploadFile, File(description="PDF、DOCX、Markdown 或 TXT 文档")],
    max_tokens: Annotated[int, Query(ge=32, le=4096)] = 512,
    chunk_overlap: Annotated[int, Query(ge=0, le=1024)] = 64,
) -> DocumentPreviewResponse:
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择一个文档。")

    suffix = Path(filename).suffix.casefold()
    if suffix not in LOADERS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="仅支持 PDF、DOCX、Markdown 和 TXT 文档。",
        )
    if chunk_overlap >= max_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重叠 Token 数必须小于单块最大 Token 数。",
        )

    try:
        with TemporaryDirectory(prefix="rag-preview-") as temporary_directory:
            temporary_path = Path(temporary_directory) / f"document{suffix}"
            size_bytes = await _save_upload(file, temporary_path)
            parsed = await run_in_threadpool(
                load_document, temporary_path, max_bytes=MAX_PREVIEW_BYTES
            )
            chunks = await run_in_threadpool(
                chunk_document,
                parsed,
                max_tokens=max_tokens,
                chunk_overlap=chunk_overlap,
            )
    except HTTPException:
        raise
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    except UnsupportedDocumentTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except DocumentParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await file.close()

    return DocumentPreviewResponse(
        filename=filename,
        media_type=parsed.media_type,
        size_bytes=size_bytes,
        page_count=parsed.page_count,
        encoding=parsed.encoding,
        character_count=parsed.character_count,
        block_count=len(parsed.blocks),
        chunk_count=len(chunks),
        total_tokens=sum(chunk.token_count for chunk in chunks),
        config=ChunkingConfigResponse(
            max_tokens=max_tokens,
            chunk_overlap=chunk_overlap,
        ),
        blocks=tuple(ParsedBlockResponse.model_validate(block) for block in parsed.blocks),
        chunks=tuple(ChunkResponse.model_validate(chunk) for chunk in chunks),
    )
