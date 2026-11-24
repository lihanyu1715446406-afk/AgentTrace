"""Overview 仪表盘聚合数据模型（M8 REST API）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CostByModel(BaseModel):
    """按模型聚合的 token 与成本。"""

    model_name: str
    total_tokens: int
    estimated_cost: float | None


class RecentTrace(BaseModel):
    """最近一条 Trace 的精简信息。"""

    trace_id: str
    name: str
    status: str
    started_at: datetime
    duration_ms: int | None


class Overview(BaseModel):
    """Overview 页所需的全局指标聚合。"""

    total_traces: int
    failed_traces: int
    total_spans: int
    total_projects: int
    total_tokens: int
    total_cost: float | None
    cost_by_model: list[CostByModel]
    recent_traces: list[RecentTrace]
