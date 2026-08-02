from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.models import DocumentStatus, MessageRole, UserRole


def test_m1_metadata_contains_core_tables() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "knowledge_bases",
        "documents",
        "document_chunks",
        "conversations",
        "messages",
    }


def test_chunk_embedding_uses_the_configured_mvp_dimension() -> None:
    embedding = Base.metadata.tables["document_chunks"].c.embedding.type
    assert isinstance(embedding, Vector)
    assert embedding.dim == 1024


def test_chunk_embedding_declares_hnsw_cosine_index() -> None:
    table = Base.metadata.tables["document_chunks"]
    index = next(item for item in table.indexes if item.name == "ix_document_chunks_embedding_hnsw")

    assert index.dialect_options["postgresql"]["using"] == "hnsw"
    assert index.dialect_options["postgresql"]["ops"] == {"embedding": "vector_cosine_ops"}


def test_persisted_enum_values_are_stable() -> None:
    assert [role.value for role in UserRole] == ["admin", "member"]
    assert [status.value for status in DocumentStatus] == [
        "pending",
        "processing",
        "ready",
        "failed",
    ]
    assert [role.value for role in MessageRole] == ["user", "assistant"]
