"""知识入库：文档 → 切分 → 向量化 → Qdrant + PostgreSQL。"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import KnowledgeDocument
from ..repositories import KnowledgeDocumentRepository
from ..schemas.rag import IngestionResult
from .chunking import split_text
from .embedding import EmbeddingProvider
from .vector_store import QdrantVectorStore


class KnowledgeIngestor:
    """把知识文档切分、向量化并写入 Qdrant 与 PostgreSQL（幂等：重入库会覆盖）。"""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embeddings: EmbeddingProvider,
        vector_store: QdrantVectorStore,
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest_document(
        self,
        *,
        document_id: str,
        title: str,
        source: str,
        content: str,
        document_type: str = "md",
        metadata: dict | None = None,
    ) -> IngestionResult:
        """入库一篇文档：切分 → 向量化 → 写 Qdrant → 写 PG（按 document_id 幂等）。"""
        chunks = split_text(content, self._chunk_size, self._chunk_overlap)
        if not chunks:
            raise ValueError("文档内容为空，无法入库")

        await self._vector_store.ensure_collection()
        vectors = await self._embeddings.aembed_documents(chunks)

        points = [
            {
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {
                    "document_id": document_id,
                    "chunk_index": i,
                    "text": text,
                    "title": title,
                    "source": source,
                    "document_type": document_type,
                },
            }
            for i, (text, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        # 幂等：先清掉旧 chunk，再写入新 chunk。
        await self._vector_store.delete_by_document(document_id)
        await self._vector_store.upsert(points)

        async with self._session_factory() as session:
            repo = KnowledgeDocumentRepository(session)
            doc = await repo.get_by_document_id(document_id)
            if doc is None:
                await repo.add(
                    KnowledgeDocument(
                        document_id=document_id,
                        title=title,
                        source=source,
                        content=content,
                        document_type=document_type,
                        metadata_=metadata,
                    )
                )
            else:
                doc.title = title
                doc.source = source
                doc.content = content
                doc.document_type = document_type
                doc.metadata_ = metadata
            await session.commit()

        return IngestionResult(
            document_id=document_id,
            title=title,
            chunks=len(chunks),
            points=len(points),
        )
