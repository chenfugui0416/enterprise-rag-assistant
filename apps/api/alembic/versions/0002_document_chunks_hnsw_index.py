"""Add the pgvector HNSW index used by cosine-distance retrieval.

Revision ID: 0002_document_chunks_hnsw_index
Revises: 0001_initial_schema
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_document_chunks_hnsw_index"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_embedding_hnsw", table_name="document_chunks")
