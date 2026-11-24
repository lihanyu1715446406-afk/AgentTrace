"""Qdrant 向量库封装：集合管理、写入点、按向量检索、按来源删除。"""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..core.config import get_settings


class QdrantVectorStore:
    """把 Qdrant 封装为「确保集合 → 写入点 → 相似度检索 → 按文档删除」的最小接口。"""

    def __init__(self, client: AsyncQdrantClient, collection: str, dim: int) -> None:
        self._client = client
        self._collection = collection
        self._dim = dim

    @classmethod
    def from_settings(cls) -> QdrantVectorStore:
        """按全局配置构建指向 Qdrant 服务端的向量库。"""
        settings = get_settings()
        return cls(
            AsyncQdrantClient(url=settings.qdrant_url),
            settings.qdrant_collection,
            settings.embedding_dim,
        )

    @property
    def collection(self) -> str:
        return self._collection

    async def ensure_collection(self) -> None:
        """确保目标集合存在；不存在则按 COSINE 距离创建。"""
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )

    async def upsert(self, points: list[dict]) -> None:
        """写入一批点，每项形如 ``{"id", "vector", "payload"}``。"""
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points
            ],
        )

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 4,
        *,
        filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """按向量做相似度检索，可选按 payload 字段做等值过滤（Metadata Filtering）。"""
        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=self._build_filter(filters),
            limit=top_k,
        )
        return [
            {
                "id": str(point.id),
                "score": float(point.score),
                "payload": point.payload or {},
            }
            for point in response.points
        ]

    async def delete_by_document(self, document_id: str) -> None:
        """删除某文档的全部 chunk（用于幂等重入库）。"""
        await self._client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            ),
        )

    @staticmethod
    def _build_filter(filters: dict[str, str] | None) -> Filter | None:
        if not filters:
            return None
        return Filter(
            must=[
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filters.items()
            ]
        )
