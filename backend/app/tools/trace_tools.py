"""Trace 查询工具（只读）。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import Trace
from ..repositories import ProjectRepository, TraceRepository
from ..schemas import TraceDetail


class TraceQueryInput(BaseModel):
    """trace_query 工具入参。"""

    trace_id: str | None = Field(default=None, description="要查询单条轨迹的 trace_id")
    project_id: str | None = Field(
        default=None, description="要列出轨迹的项目（项目名或 UUID 字符串）"
    )
    limit: int = Field(default=10, ge=1, le=100, description="返回条数上限")


def _trace_to_dict(trace: Trace) -> dict:
    return TraceDetail(
        trace_id=trace.trace_id,
        project_id=str(trace.project_id),
        name=trace.name,
        status=trace.status,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_ms=trace.duration_ms,
        metadata=trace.metadata_,
    ).model_dump(mode="json")


def build_trace_query_tool(session_factory: async_sessionmaker[AsyncSession]) -> StructuredTool:
    """构建 TraceQueryTool：查询单条 trace 或列出某项目下的 traces。"""

    async def _query(
        trace_id: str | None = None,
        project_id: str | None = None,
        limit: int = 10,
    ) -> str:
        if trace_id:
            async with session_factory() as session:
                repo = TraceRepository(session)
                trace = await repo.get_by_trace_id(trace_id)
                if trace is None:
                    return json.dumps({"error": f"未找到 trace_id={trace_id}"}, ensure_ascii=False)
                return json.dumps({"trace": _trace_to_dict(trace)}, ensure_ascii=False)

        if project_id:
            async with session_factory() as session:
                pid = await ProjectRepository(session).resolve(project_id)
                if pid is None:
                    return json.dumps(
                        {"error": f"未找到项目：{project_id}（支持项目名或 UUID）"},
                        ensure_ascii=False,
                    )
                traces = await TraceRepository(session).list_by_project(pid, limit=limit)
                return json.dumps(
                    {"traces": [_trace_to_dict(t) for t in traces]}, ensure_ascii=False
                )

        return json.dumps({"error": "必须提供 trace_id 或 project_id 之一"}, ensure_ascii=False)

    return StructuredTool.from_function(
        name="trace_query",
        description=(
            "查询 Agent 执行轨迹（trace）。提供 trace_id 时返回单条轨迹详情；"
            "提供 project_id（项目名或 UUID）时返回该项目下的轨迹列表。"
            "用于了解一次任务的状态、耗时与元数据。"
        ),
        args_schema=TraceQueryInput,
        coroutine=_query,
    )
