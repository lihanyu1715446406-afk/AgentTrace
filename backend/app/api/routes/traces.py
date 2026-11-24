"""Trace 查询（展示）路由：读取 SDK 采集的真实数据。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models import Span, TokenUsage, Trace
from ...repositories import SpanRepository, TokenUsageRepository, TraceRepository
from ..dependencies import authenticate_project

router = APIRouter(prefix="/traces", tags=["traces"])


def _trace_dict(trace: Trace) -> dict:
    return {
        "trace_id": trace.trace_id,
        "project_id": str(trace.project_id),
        "name": trace.name,
        "status": trace.status,
        "started_at": trace.started_at,
        "ended_at": trace.ended_at,
        "duration_ms": trace.duration_ms,
        "metadata": trace.metadata_,
    }


def _span_dict(span: Span) -> dict:
    return {
        "span_id": span.span_id,
        "trace_id": span.trace_id,
        "parent_span_id": span.parent_span_id,
        "name": span.name,
        "span_type": span.span_type,
        "status": span.status,
        "started_at": span.started_at,
        "ended_at": span.ended_at,
        "duration_ms": span.duration_ms,
        "input": span.input,
        "output": span.output,
        "error": span.error,
    }


def _usage_dict(usage: TokenUsage) -> dict:
    return {
        "model_name": usage.model_name,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "estimated_cost": (
            float(usage.estimated_cost) if usage.estimated_cost is not None else None
        ),
        "currency": usage.currency,
    }


@router.get("")
async def list_traces(
    project_id: uuid.UUID = Depends(authenticate_project),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """按项目列出已采集的 Trace（鉴权通过后）。"""
    traces = await TraceRepository(db).list_by_project(project_id, limit=100)
    return [_trace_dict(t) for t in traces]


@router.get("/{trace_id}")
async def get_trace(
    trace_id: str,
    project_id: uuid.UUID = Depends(authenticate_project),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """查询单条 Trace 的完整结构（spans 树 + token 用量 + 成本聚合）。"""
    trace = await TraceRepository(db).get_by_trace_id(trace_id)
    if trace is None or trace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Trace 不存在")
    spans = await SpanRepository(db).list_by_trace(trace_id)
    usages = await TokenUsageRepository(db).list_by_trace(trace_id)
    cost = await TokenUsageRepository(db).aggregate_by_trace(trace_id)
    return {
        "trace": _trace_dict(trace),
        "spans": [_span_dict(s) for s in spans],
        "token_usages": [_usage_dict(u) for u in usages],
        "cost": cost,
    }
