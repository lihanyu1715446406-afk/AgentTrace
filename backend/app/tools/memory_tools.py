"""记忆检索工具（只读）：memory_search。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from ..memory.manager import MemoryManager
from ..schemas.memory import MemoryType


class MemorySearchInput(BaseModel):
    """memory_search 工具入参。"""

    query: str = Field(description="要检索的历史经历/知识的关键词")
    project_id: str = Field(description="项目 ID（UUID 字符串）")
    memory_type: str | None = Field(
        default=None, description="记忆类型过滤：EPISODIC / SEMANTIC / PROCEDURAL（可选）"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="返回的最相关记忆条数")


def build_memory_search_tool(manager: MemoryManager) -> StructuredTool:
    """构建 memory_search 工具：检索历史记忆（情景/语义），返回带出处的记忆列表。"""

    async def _search(
        query: str,
        project_id: str,
        memory_type: str | None = None,
        top_k: int = 5,
    ) -> str:
        mtype: MemoryType | None = None
        if memory_type:
            try:
                mtype = MemoryType(memory_type.upper())
            except ValueError:
                return json.dumps(
                    {"error": f"非法的 memory_type: {memory_type}"}, ensure_ascii=False
                )
        try:
            result = await manager.recall(project_id, query, memory_type=mtype, limit=top_k)
        except ValueError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)

    return StructuredTool.from_function(
        name="memory_search",
        description=(
            "检索历史记忆库，返回与关键词相关的历史诊断经历（情景记忆）或提炼出的知识"
            "（语义记忆）。适合回答『这次问题之前遇到过吗』『历史上有无相似案例』类问题；"
            "可选按 memory_type 过滤。"
        ),
        args_schema=MemorySearchInput,
        coroutine=_search,
    )
