"""知识库路由（只读）：列出已入库的知识文档，供 Dashboard 展示。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...repositories import KnowledgeDocumentRepository
from ...schemas import KnowledgeDocumentRead

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeDocumentRead])
async def list_documents(
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeDocumentRead]:
    """列出全部知识文档（最近入库优先）。"""
    documents = await KnowledgeDocumentRepository(db).list()
    return [
        KnowledgeDocumentRead(
            document_id=d.document_id,
            title=d.title,
            source=d.source,
            document_type=d.document_type,
            created_at=d.created_at,
        )
        for d in documents
    ]
