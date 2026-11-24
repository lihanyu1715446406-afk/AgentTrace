"""Span 查询工具（只读）。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import Span
from ..repositories import SpanRepository
from ..schemas import SpanDetail


class SpanQueryInput(BaseModel):
    """span_query 工具入参。"""

    trace_id: str | None = Field(default=None, description="按轨迹查询其所有 span")
    span_id: str | None = Field(default=None, description="查询单条 span")
    limit: int = Field(default=100, ge=1, le=500, description="返回条数上限")


def _span_to_dict(span: Span) -> dict:
    return SpanDetail(
        span_id=span.span_id,
        trace_id=span.trace_id,
        parent_span_id=span.parent_span_id,
        name=span.name,
        span_type=span.span_type,
        status=span.status,
        started_at=span.started_at,
        ended_at=span.ended_at,
        duration_ms=span.duration_ms,
        input=span.input,
        output=span.output,
        error=span.error,
    ).model_dump(mode="json")


def build_span_query_tool(session_factory: async_sessionmaker[AsyncSession]) -> StructuredTool:
    """构建 SpanQueryTool：查询单条 span 或某轨迹下的全部 span。"""

    async def _query(
        trace_id: str | None = None,
        span_id: str | None = None,
        limit: int = 100,
    ) -> str:
        async with session_factory() as session:
            repo = SpanRepository(session)

            if span_id:
                span = await repo.get_by_span_id(span_id)
                if span is None:
                    return json.dumps({"error": f"未找到 span_id={span_id}"}, ensure_ascii=False)
                return json.dumps({"span": _span_to_dict(span)}, ensure_ascii=False)

            if trace_id:
                spans = await repo.list_by_trace(trace_id)
                return json.dumps(
                    {"spans": [_span_to_dict(s) for s in spans[:limit]]},
                    ensure_ascii=False,
                )

            return json.dumps({"error": "必须提供 span_id 或 trace_id 之一"}, ensure_ascii=False)

    return StructuredTool.from_function(
        name="span_query",
        description=(
            "查询执行单元（span）。提供 span_id 返回单条 span 详情；"
            "提供 trace_id 返回该轨迹下的全部 span（含类型、状态、耗时、输入输出、错误）。"
        ),
        args_schema=SpanQueryInput,
        coroutine=_query,
    )
