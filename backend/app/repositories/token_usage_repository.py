"""Token 用量与成本查询仓库（只读）。"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from ..models import TokenUsage, Trace
from .base import BaseRepository


class TokenUsageRepository(BaseRepository):
    """聚合 Token 用量与成本的只读仓库。"""

    async def list_by_trace(self, trace_id: str) -> list[TokenUsage]:
        result = await self.session.execute(
            select(TokenUsage).where(TokenUsage.trace_id == trace_id)
        )
        return list(result.scalars().all())

    async def aggregate_by_trace(self, trace_id: str) -> dict:
        """按单条 trace 聚合 token 与成本（按模型分组）。"""
        return await self._aggregate(trace_id=trace_id)

    async def aggregate_by_project(self, project_id: uuid.UUID) -> dict:
        """按项目聚合 token 与成本（按模型分组）。"""
        return await self._aggregate(project_id=project_id)

    async def _aggregate(
        self, *, project_id: uuid.UUID | None = None, trace_id: str | None = None
    ) -> dict:
        stmt = select(
            TokenUsage.model_name,
            func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.estimated_cost).label("estimated_cost"),
        ).group_by(TokenUsage.model_name)

        if project_id is not None:
            stmt = stmt.join(Trace, TokenUsage.trace_id == Trace.trace_id).where(
                Trace.project_id == project_id
            )
        elif trace_id is not None:
            stmt = stmt.where(TokenUsage.trace_id == trace_id)

        rows = (await self.session.execute(stmt)).all()

        by_model = [
            {
                "model_name": row.model_name,
                "prompt_tokens": int(row.prompt_tokens or 0),
                "completion_tokens": int(row.completion_tokens or 0),
                "total_tokens": int(row.total_tokens or 0),
                "estimated_cost": row.estimated_cost,
            }
            for row in rows
        ]

        total_prompt = sum(m["prompt_tokens"] for m in by_model)
        total_completion = sum(m["completion_tokens"] for m in by_model)
        total_tokens = sum(m["total_tokens"] for m in by_model)
        costs = [m["estimated_cost"] for m in by_model if m["estimated_cost"] is not None]
        total_cost: Decimal | None = sum(costs, Decimal("0")) if costs else None

        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_model": by_model,
        }
