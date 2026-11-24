"""Memory（M5）相关的 Pydantic 数据模型。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    """长期记忆的类型（与数据库设计 2.8 的取值一致）。"""

    EPISODIC = "EPISODIC"  # 情景记忆：一次诊断经历/事件
    SEMANTIC = "SEMANTIC"  # 语义记忆：从经历中提炼的可复用知识
    PROCEDURAL = "PROCEDURAL"  # 程序性记忆：how-to（本里程碑预留，未落地）


class MemoryRecordRead(BaseModel):
    """一条长期记忆的读取结果。"""

    memory_id: str
    project_id: str
    memory_type: str
    content: str
    source_task_id: str | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime | None


class MemoryWriteResult(BaseModel):
    """一次记忆写入的结构化结果。"""

    memory_id: str
    memory_type: str
    content: str
    created: bool = Field(description="True=新建；False=去重命中后更新而非新增")
    updated_at: datetime | None


class MemorySearchResult(BaseModel):
    """一次记忆检索的结构化结果。"""

    query: str
    memory_type: str | None
    hits: list[MemoryRecordRead] = Field(default_factory=list)


class ConsolidationDraft(BaseModel):
    """LLM 从多条情景记忆中提炼出的语义记忆草稿。"""

    content: str = Field(description="提炼出的可复用知识/结论正文")


class ConsolidationResult(BaseModel):
    """一次记忆巩固（episodic → semantic）的结果。"""

    source_memory_ids: list[str] = Field(
        default_factory=list, description="参与巩固的源情景记忆 id"
    )
    semantic_memory: MemoryWriteResult | None = Field(default=None)
    skipped_reason: str | None = Field(default=None)


class WorkingSnapshot(BaseModel):
    """WorkingMemory（短期记忆 + Checkpointer）一次执行/恢复后的快照。"""

    thread_id: str
    user_query: str
    draft: str | None
    approved: bool | None
    final_report: str | None
    interrupted: bool = Field(description="True=停在人工确认点（可 resume）；False=已走完定稿")
