"""Span 查询仓库（只读）。"""

from __future__ import annotations

from sqlalchemy import select

from ..models import Span
from .base import BaseRepository


class SpanRepository(BaseRepository):
    """查询 Span 数据的只读仓库。"""

    async def get_by_span_id(self, span_id: str) -> Span | None:
        result = await self.session.execute(select(Span).where(Span.span_id == span_id))
        return result.scalar_one_or_none()

    async def list_by_trace(self, trace_id: str) -> list[Span]:
        result = await self.session.execute(
            select(Span).where(Span.trace_id == trace_id).order_by(Span.started_at.asc())
        )
        return list(result.scalars().all())
