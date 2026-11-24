"""SDK 数据上报（ingest）与项目接入相关的 Pydantic 数据模型。

SDK 通过 HTTP 上报（ADR-0006），本模块定义上报 body 与回执结构。成本金额在 JSON
边界用 ``float`` 表示（避免 Decimal 的 JSON 序列化歧义），落库时再由服务层转回
``Decimal``。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SpanIngest(BaseModel):
    """一条 Span 的上报数据。"""

    span_id: str = Field(description="Span 唯一标识")
    parent_span_id: str | None = Field(default=None, description="父 Span（根为 null）")
    name: str = Field(description="Span 名称")
    span_type: str = Field(description="执行类型：llm/tool/chain/retrieval/...")
    status: str = Field(default="success", description="执行状态")
    started_at: datetime = Field(description="开始时间")
    ended_at: datetime | None = Field(default=None, description="结束时间")
    duration_ms: int | None = Field(default=None, description="耗时（毫秒）")
    input: dict | None = Field(default=None, description="输入")
    output: dict | None = Field(default=None, description="输出")
    error: dict | None = Field(default=None, description="错误信息")
    metadata: dict | None = Field(default=None, description="扩展信息")


class TokenUsageIngest(BaseModel):
    """一条 Token 消耗记录。"""

    span_id: str = Field(description="所属 Span")
    model_name: str = Field(description="模型名")
    prompt_tokens: int = Field(default=0, description="输入 token")
    completion_tokens: int = Field(default=0, description="输出 token")
    total_tokens: int = Field(default=0, description="总 token")
    estimated_cost: float | None = Field(default=None, description="估算成本")
    currency: str = Field(default="USD", description="币种")


class TraceIngest(BaseModel):
    """一次完整 Trace 的上报数据（含 spans 与 token usages）。"""

    project_id: uuid.UUID = Field(description="所属项目")
    trace_id: str = Field(description="Trace 唯一标识")
    name: str = Field(description="任务名称")
    status: str = Field(default="success", description="执行状态")
    started_at: datetime = Field(description="开始时间")
    ended_at: datetime | None = Field(default=None, description="结束时间")
    duration_ms: int | None = Field(default=None, description="耗时（毫秒）")
    metadata: dict | None = Field(default=None, description="扩展信息")
    spans: list[SpanIngest] = Field(default_factory=list)
    token_usages: list[TokenUsageIngest] = Field(default_factory=list)


class IngestResult(BaseModel):
    """一次上报的回执。"""

    trace_id: str
    span_count: int
    token_usage_count: int


class ProjectCreate(BaseModel):
    """创建项目的请求体。"""

    name: str = Field(description="项目名")


class ProjectCreateResult(BaseModel):
    """创建项目的返回体（api_key 仅此一次返回明文）。"""

    project_id: uuid.UUID
    name: str
    api_key: str


class ProjectRead(BaseModel):
    """项目列表项（供 Dashboard 选择项目）。"""

    project_id: uuid.UUID
    name: str
