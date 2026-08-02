"""SQLAlchemy models imported here so Alembic sees the complete metadata."""

from app.models.conversation import Conversation, Message
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus, MessageRole, UserRole
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User

__all__ = [
    "Conversation",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "KnowledgeBase",
    "Message",
    "MessageRole",
    "User",
    "UserRole",
]
