"""测试共享假件：确定性 embedding + 内存 Qdrant 向量库。

用于隔离外部 SiliconFlow API 与 Qdrant 服务端（RAG 与语义记忆测试共用）。
"""

from __future__ import annotations

import math

from qdrant_client import AsyncQdrantClient

from backend.app.rag.vector_store import QdrantVectorStore


class FakeEmbedding:
    """确定性字符哈希向量：同（近）文本→相近向量，测试中隔离外部 embedding API。"""

    dim = 16

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def aembed_query(self, text: str) -> list[float]:
        return self._embed(text)

    @staticmethod
    def _embed(text: str) -> list[float]:
        vec = [0.0] * FakeEmbedding.dim
        for ch in text:
            vec[ord(ch) % FakeEmbedding.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


async def make_in_memory_store(collection: str = "test") -> QdrantVectorStore:
    """构建并 ensure_collection 的内存 Qdrant 向量库（隔离外部服务端）。"""
    store = QdrantVectorStore(AsyncQdrantClient(":memory:"), collection, FakeEmbedding.dim)
    await store.ensure_collection()
    return store
