"""长期记忆仓库：写入、查询、关键词检索、去重。"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from ..models import MemoryRecord
from .base import BaseRepository


class MemoryRecordRepository(BaseRepository):
    """``MemoryRecord`` 的数据访问：写入、按 id 查询、按项目列出、关键词检索、去重。"""

    async def add(self, memory: MemoryRecord) -> MemoryRecord:
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get_by_memory_id(self, memory_id: str) -> MemoryRecord | None:
        result = await self.session.execute(
            select(MemoryRecord).where(MemoryRecord.memory_id == memory_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        memory_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MemoryRecord]:
        """按项目（可选按类型）列出记忆，按创建时间倒序。"""
        stmt = select(MemoryRecord).where(MemoryRecord.project_id == project_id)
        if memory_type is not None:
            stmt = stmt.where(MemoryRecord.memory_type == memory_type)
        stmt = stmt.order_by(MemoryRecord.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_duplicate(
        self, project_id: uuid.UUID, memory_type: str, content: str
    ) -> MemoryRecord | None:
        """精确内容匹配去重：同项目同类型下，若存在内容完全相同的记忆则返回它。"""
        result = await self.session.execute(
            select(MemoryRecord).where(
                MemoryRecord.project_id == project_id,
                MemoryRecord.memory_type == memory_type,
                MemoryRecord.content == content,
            )
        )
        return result.scalars().first()

    async def search(
        self,
        project_id: uuid.UUID,
        query: str,
        memory_type: str | None = None,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """按关键词检索记忆（PG ``ILIKE``，大小写不敏感，按创建时间倒序）。"""
        pattern = f"%{query.strip()}%"
        stmt = select(MemoryRecord).where(
            MemoryRecord.project_id == project_id,
            MemoryRecord.content.ilike(pattern),
        )
        if memory_type is not None:
            stmt = stmt.where(MemoryRecord.memory_type == memory_type)
        stmt = stmt.order_by(MemoryRecord.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
