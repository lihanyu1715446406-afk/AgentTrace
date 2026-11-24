"""知识检索：查询向量化 → Qdrant 相似度检索 → 带来源的 chunk 列表。"""

from __future__ import annotations

from ..schemas.rag import KnowledgeChunk
from .embedding import EmbeddingProvider
from .vector_store import QdrantVectorStore


class KnowledgeRetriever:
    """检索知识库：embed(query) → 向量检索 → ``KnowledgeChunk``（保留来源）。"""

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vector_store: QdrantVectorStore,
    ) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        *,
        document_type: str | None = None,
        source: str | None = None,
    ) -> list[KnowledgeChunk]:
        """返回与查询最相关的知识片段，按相似度降序。"""
        vector = await self._embeddings.aembed_query(query)
        filters: dict[str, str] = {}
        if document_type:
            filters["document_type"] = document_type
        if source:
            filters["source"] = source
        hits = await self._vector_store.search(vector, top_k, filters=filters)
        return [
            KnowledgeChunk(
                chunk_id=h["id"],
                document_id=h["payload"].get("document_id", ""),
                chunk_index=h["payload"].get("chunk_index", 0),
                text=h["payload"].get("text", ""),
                title=h["payload"].get("title", ""),
                source=h["payload"].get("source", ""),
                document_type=h["payload"].get("document_type", ""),
                score=h["score"],
            )
            for h in hits
        ]
