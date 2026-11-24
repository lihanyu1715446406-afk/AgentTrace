"""Overview 仪表盘聚合仓库（只读）。"""

from __future__ import annotations

from sqlalchemy import func, select

from ..models import Project, Span, TokenUsage, Trace
from .base import BaseRepository


class OverviewRepository(BaseRepository):
    """聚合全局指标，供仪表盘 Overview 页展示（M8 REST API）。"""

    async def summary(self, limit: int = 10) -> dict:
        """返回 trace/span/project 计数、token 成本汇总与最近 trace 列表。"""
        total_traces = await self.session.scalar(select(func.count()).select_from(Trace)) or 0
        failed_traces = (
            await self.session.scalar(
                select(func.count()).select_from(Trace).where(Trace.status == "failed")
            )
            or 0
        )
        total_spans = await self.session.scalar(select(func.count()).select_from(Span)) or 0
        total_projects = await self.session.scalar(select(func.count()).select_from(Project)) or 0
        total_tokens = (
            await self.session.scalar(
                select(func.coalesce(func.sum(TokenUsage.total_tokens), 0)).select_from(TokenUsage)
            )
            or 0
        )
        total_cost = await self.session.scalar(
            select(func.sum(TokenUsage.estimated_cost)).select_from(TokenUsage)
        )

        by_model_rows = (
            await self.session.execute(
                select(
                    TokenUsage.model_name,
                    func.sum(TokenUsage.total_tokens).label("total_tokens"),
                    func.sum(TokenUsage.estimated_cost).label("estimated_cost"),
                ).group_by(TokenUsage.model_name)
            )
        ).all()

        recent_rows = list(
            (
                await self.session.execute(
                    select(Trace).order_by(Trace.started_at.desc()).limit(limit)
                )
            )
            .scalars()
            .all()
        )

        return {
            "total_traces": int(total_traces),
            "failed_traces": int(failed_traces),
            "total_spans": int(total_spans),
            "total_projects": int(total_projects),
            "total_tokens": int(total_tokens),
            "total_cost": float(total_cost) if total_cost is not None else None,
            "cost_by_model": [
                {
                    "model_name": row.model_name,
                    "total_tokens": int(row.total_tokens or 0),
                    "estimated_cost": (
                        float(row.estimated_cost) if row.estimated_cost is not None else None
                    ),
                }
                for row in by_model_rows
            ],
            "recent_traces": [
                {
                    "trace_id": t.trace_id,
                    "name": t.name,
                    "status": t.status,
                    "started_at": t.started_at,
                    "duration_ms": t.duration_ms,
                }
                for t in recent_rows
            ],
        }
