"""知识检索工具（只读）：knowledge_search。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..rag.retriever import KnowledgeRetriever


class KnowledgeSearchInput(BaseModel):
    """knowledge_search 工具入参。"""

    query: str = Field(description="要检索的知识问题或关键词")
    document_type: str | None = Field(default=None, description="按文档类型等值过滤（可选）")
    source: str | None = Field(default=None, description="按来源等值过滤（可选）")
    top_k: int = Field(default=4, description="返回的最相关片段数")


def build_knowledge_search_tool(retriever: KnowledgeRetriever) -> StructuredTool:
    """构建 knowledge_search 工具：向量检索知识库，返回带来源的片段。"""

    async def _search(
        query: str,
        document_type: str | None = None,
        source: str | None = None,
        top_k: int = 4,
    ) -> str:
        hits = await retriever.retrieve(
            query,
            top_k=top_k,
            document_type=document_type,
            source=source,
        )
        return json.dumps(
            {"query": query, "hits": [h.model_dump(mode="json") for h in hits]},
            ensure_ascii=False,
        )

    return StructuredTool.from_function(
        name="knowledge_search",
        description=(
            "检索知识库，返回与问题最相关的知识片段（含标题、来源、文本与相似度）。"
            "适合回答运维手册、故障排查、最佳实践等知识型问题；可选按 document_type / source 过滤。"
        ),
        args_schema=KnowledgeSearchInput,
        coroutine=_search,
    )
