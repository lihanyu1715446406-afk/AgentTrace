"""语义记忆的生产装配：用真实 embedding + Qdrant 记忆集合构建 MemoryManager。"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.config import get_settings
from ..core.embedding import get_embedding
from ..rag.vector_store import QdrantVectorStore
from .manager import MemoryManager


def build_memory_vector_index() -> QdrantVectorStore:
    """构建指向 Qdrant 记忆集合的向量索引。"""
    settings = get_settings()
    return QdrantVectorStore(
        AsyncQdrantClient(url=settings.qdrant_url),
        settings.qdrant_memory_collection,
        settings.embedding_dim,
    )


def build_semantic_memory_manager(
    session_factory: async_sessionmaker[AsyncSession],
    **kwargs,
) -> MemoryManager:
    """构建启用语义检索/去重的 MemoryManager（embedding + Qdrant 均已装配）。"""
    return MemoryManager(
        session_factory,
        embedding=get_embedding(),
        vector_index=build_memory_vector_index(),
        **kwargs,
    )
