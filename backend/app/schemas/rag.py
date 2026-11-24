"""RAG 相关的 Pydantic 数据模型（知识检索结果与入库结果）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeChunk(BaseModel):
    """检索命中的一个知识片段，携带来源信息。"""

    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    title: str
    source: str
    document_type: str
    score: float


class KnowledgeSearchResult(BaseModel):
    """一次知识检索的结构化结果。"""

    query: str
    hits: list[KnowledgeChunk] = Field(default_factory=list)


class IngestionResult(BaseModel):
    """一次文档入库的结构化结果。"""

    document_id: str
    title: str
    chunks: int
    points: int


class KnowledgeDocumentRead(BaseModel):
    """知识库文档的精简信息（Dashboard 知识库页）。"""

    document_id: str
    title: str
    source: str
    document_type: str
    created_at: datetime
