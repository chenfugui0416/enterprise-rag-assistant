"""Minimal end-to-end RAG routes for the local product demonstration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.routes.document_preview import _save_upload
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Document, DocumentChunk, DocumentStatus, KnowledgeBase, User
from app.rag.embeddings import DocumentIngestionService, build_embedding_service
from app.rag.generation import GroundedAnswerService
from app.rag.loaders import LOADERS, DocumentParseError, load_document
from app.rag.providers.factory import get_llm_provider
from app.rag.retrieval import MimirQSearchService, VectorSearchService
from app.schemas.demo_rag import (
    CitationResponse,
    IndexResponse,
    QueryRequest,
    QueryResponse,
    RetrievedResponse,
)

router = APIRouter(prefix="/demo", tags=["rag-demo"])
DEMO_EMAIL = "demo@enterprise-rag.local"
DEMO_STORAGE = Path(__file__).resolve().parents[5] / "data" / "storage" / "demo"


async def _get_demo_knowledge_base(session: AsyncSession) -> KnowledgeBase:
    user = await session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(email=DEMO_EMAIL, password_hash="demo-only", display_name="演示用户")
        session.add(user)
        await session.flush()
    knowledge_base = await session.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.owner_id == user.id,
            KnowledgeBase.name == "演示企业知识库",
        )
    )
    if knowledge_base is None:
        knowledge_base = KnowledgeBase(
            owner_id=user.id,
            name="演示企业知识库",
            description="用于学习文档解析、向量检索和引用回答。",
        )
        session.add(knowledge_base)
        await session.flush()
    return knowledge_base


@router.post("/index", response_model=IndexResponse, summary="索引一份演示文档")
async def index_demo_document(
    file: Annotated[UploadFile, File(description="PDF、DOCX、Markdown 或 TXT 文档")],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IndexResponse:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.casefold()
    if not filename:
        raise HTTPException(status_code=400, detail="请选择一个文档。")
    if suffix not in LOADERS:
        raise HTTPException(status_code=415, detail="仅支持 PDF、DOCX、Markdown 和 TXT 文档。")

    DEMO_STORAGE.mkdir(parents=True, exist_ok=True)
    temporary_directory = TemporaryDirectory(prefix="rag-index-")
    try:
        temporary_path = Path(temporary_directory.name) / f"document{suffix}"
        size_bytes = await _save_upload(file, temporary_path)
        digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()
        knowledge_base = await _get_demo_knowledge_base(session)
        existing = await session.scalar(
            select(Document).where(
                Document.knowledge_base_id == knowledge_base.id,
                Document.sha256 == digest,
            )
        )
        if existing is not None and existing.status == DocumentStatus.READY:
            chunk_count = await session.scalar(
                select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == existing.id)
            )
            await file.close()
            return IndexResponse(
                document_id=existing.id,
                filename=existing.filename,
                status=existing.status.value,
                chunk_count=int(chunk_count or 0),
                embedding_model=get_settings().embedding_model,
                duplicate=True,
            )

        storage_path = DEMO_STORAGE / f"{digest}{suffix}"
        storage_path.write_bytes(temporary_path.read_bytes())
        parsed = await run_in_threadpool(load_document, temporary_path)
        document = existing or Document(
            knowledge_base_id=knowledge_base.id,
            filename=filename,
            storage_path=str(storage_path),
            mime_type=parsed.media_type,
            size_bytes=size_bytes,
            sha256=digest,
        )
        if existing is None:
            session.add(document)
            await session.flush()
        else:
            document.filename = filename
            document.storage_path = str(storage_path)
            document.mime_type = parsed.media_type
            document.size_bytes = size_bytes
        embedding_service = build_embedding_service()
        result = await DocumentIngestionService(embedding_service).ingest(
            session, document.id, parsed
        )
        await session.refresh(document)
        return IndexResponse(
            document_id=document.id,
            filename=filename,
            status=document.status.value,
            chunk_count=result.chunk_count,
            embedding_model=result.embedding_model,
        )
    except DocumentParseError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        temporary_directory.cleanup()
        await file.close()


@router.post("/query", response_model=QueryResponse, summary="查询演示知识库")
async def query_demo_knowledge_base(
    request: QueryRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> QueryResponse:
    knowledge_base = await session.scalar(
        select(KnowledgeBase).where(KnowledgeBase.name == "演示企业知识库")
    )
    if knowledge_base is None:
        raise HTTPException(status_code=404, detail="请先索引一份文档。")
    settings = get_settings()
    try:
        search_service = (
            MimirQSearchService(settings)
            if settings.mimirq_enabled
            else VectorSearchService(build_embedding_service(settings))
        )
        answer = await GroundedAnswerService(
            search_service,
            get_llm_provider(),
            confidence_threshold=request.confidence_threshold,
        ).answer(
            session,
            knowledge_base.id,
            request.question,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    citations = tuple(
        CitationResponse(
            document_id=citation.document_id,
            document_name=citation.document_name,
            chunk_index=citation.chunk_index,
            score=citation.score,
            page_number=citation.page_number,
            section_title=citation.section_title,
            content=citation.content,
        )
        for citation in answer.citations
    )
    retrieved = tuple(
        RetrievedResponse(
            document_id=result.document_id,
            document_name=result.document_name,
            chunk_index=result.chunk_index,
            score=result.score,
            page_number=result.page_number,
            section_title=result.section_title,
            content=result.content,
        )
        for result in answer.retrieved
    )
    return QueryResponse(
        question=answer.question,
        answer=answer.answer,
        refused=answer.refused,
        model_name=answer.model_name,
        citations=citations,
        retrieved=retrieved,
    )
