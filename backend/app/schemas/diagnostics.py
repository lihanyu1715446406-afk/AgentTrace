"""诊断相关的 Pydantic 数据模型（工具输出与 Agent 结果）。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TraceDetail(BaseModel):
    """单条 Trace 的结构化详情。"""

    trace_id: str
    project_id: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    metadata: dict | None


class SpanDetail(BaseModel):
    """单条 Span 的结构化详情。"""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    name: str
    span_type: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    input: dict | None
    output: dict | None
    error: dict | None


class ModelCost(BaseModel):
    """按模型聚合的用量与成本。"""

    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: Decimal | None


class CostSummary(BaseModel):
    """Token 用量与成本的汇总。"""

    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: Decimal | None
    by_model: list[ModelCost]


class ToolCallRecord(BaseModel):
    """一次工具调用的记录。"""

    tool_name: str
    args: dict
    output: str


class AgentResult(BaseModel):
    """Agent 一次诊断的结构化结果。"""

    query: str
    answer: str
    tool_calls: list[ToolCallRecord]


class DiagnoseRequest(BaseModel):
    """AI 诊断接口（M8 REST API）的请求体。"""

    query: str = Field(min_length=1, description="自然语言诊断提问")
