"""知识文档仓库（入库写入 + 查询）。"""

from __future__ import annotations

from sqlalchemy import select

from ..models import KnowledgeDocument
from .base import BaseRepository


class KnowledgeDocumentRepository(BaseRepository):
    """知识文档的数据访问：支持写入（入库）与查询。"""

    async def add(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_by_document_id(self, document_id: str) -> KnowledgeDocument | None:
        result = await self.session.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.document_id == document_id)
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int = 50, offset: int = 0) -> list[KnowledgeDocument]:
        result = await self.session.execute(
            select(KnowledgeDocument)
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
