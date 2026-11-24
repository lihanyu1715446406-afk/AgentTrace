"""Trace 查询仓库（只读）。"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from ..models import Trace
from .base import BaseRepository


class TraceRepository(BaseRepository):
    """查询 Trace 数据的只读仓库。"""

    async def get_by_trace_id(self, trace_id: str) -> Trace | None:
        result = await self.session.execute(select(Trace).where(Trace.trace_id == trace_id))
        return result.scalar_one_or_none()

    async def list_by_project(
        self, project_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[Trace]:
        result = await self.session.execute(
            select(Trace)
            .where(Trace.project_id == project_id)
            .order_by(Trace.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
