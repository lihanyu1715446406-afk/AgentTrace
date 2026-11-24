"""AgentTrace MCP Server：把只读诊断工具以 MCP 协议开放给其他 Agent。

M8 目标（开发路线图）之一。用 MCP Python SDK 的 ``MCPServer`` 注册三个只读工具，
与 M1 的 LangChain 工具一一对应，返回同样的 JSON 字符串，保证「工具语义」只有一处来源：

- ``trace_query``：查单条 trace 详情 / 列某项目 trace 列表。
- ``span_query``：查单条 span / 列某 trace 的全部 span。
- ``cost_analysis``：按项目 / 轨迹聚合 token 与成本。

启动（stdio，默认传输）：
    uv run python -m mcp_server.server

MCP Client 通过 stdio 连接本进程即可调用上述工具（演示见 ``scripts/mcp_client_demo.py``）。
"""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.app.core.database import async_session_factory
from backend.app.repositories import (
    ProjectRepository,
    SpanRepository,
    TokenUsageRepository,
    TraceRepository,
)
from backend.app.schemas import CostSummary, SpanDetail, TraceDetail


def _trace_to_dict(trace) -> dict:
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


def _span_to_dict(span) -> dict:
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


async def query_trace(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    trace_id: str | None = None,
    project_id: str | None = None,
    limit: int = 10,
) -> str:
    """trace_query 的实现：查单条 trace 或列出某项目下的 traces。"""
    if trace_id:
        async with session_factory() as session:
            trace = await TraceRepository(session).get_by_trace_id(trace_id)
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
            return json.dumps({"traces": [_trace_to_dict(t) for t in traces]}, ensure_ascii=False)

    return json.dumps({"error": "必须提供 trace_id 或 project_id 之一"}, ensure_ascii=False)


async def query_span(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    trace_id: str | None = None,
    span_id: str | None = None,
    limit: int = 100,
) -> str:
    """span_query 的实现：查单条 span 或列出某 trace 下的全部 span。"""
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


async def analyze_cost(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    project_id: str | None = None,
    trace_id: str | None = None,
) -> str:
    """cost_analysis 的实现：按项目 / 轨迹聚合 token 用量与成本。"""
    if not project_id and not trace_id:
        return json.dumps({"error": "必须提供 project_id 或 trace_id 之一"}, ensure_ascii=False)

    async with session_factory() as session:
        repo = TokenUsageRepository(session)
        if project_id:
            pid = await ProjectRepository(session).resolve(project_id)
            if pid is None:
                return json.dumps(
                    {"error": f"未找到项目：{project_id}（支持项目名或 UUID）"},
                    ensure_ascii=False,
                )
            summary = await repo.aggregate_by_project(pid)
        elif trace_id:
            summary = await repo.aggregate_by_trace(trace_id)
        else:  # 防御性兜底，正常不会到达
            return json.dumps({"error": "必须提供 project_id 或 trace_id 之一"}, ensure_ascii=False)

        return json.dumps(
            {"cost": CostSummary(**summary).model_dump(mode="json")},
            ensure_ascii=False,
        )


def build_server(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> MCPServer:
    """构建 MCPServer 实例并注册只读诊断工具。

    ``session_factory`` 允许注入（默认用全局生产会话工厂），使测试可指向隔离库。
    """
    sf = session_factory or async_session_factory
    mcp = MCPServer("AgentTrace")

    @mcp.tool()
    async def trace_query(
        trace_id: str | None = None,
        project_id: str | None = None,
        limit: int = 10,
    ) -> str:
        """查询执行轨迹：trace_id 返回单条详情，project_id（项目名或 UUID）返回项目下轨迹列表。"""
        return await query_trace(sf, trace_id=trace_id, project_id=project_id, limit=limit)

    @mcp.tool()
    async def span_query(
        trace_id: str | None = None,
        span_id: str | None = None,
        limit: int = 100,
    ) -> str:
        """查询执行单元：span_id 返回单条详情，trace_id 返回该轨迹全部 span。"""
        return await query_span(sf, trace_id=trace_id, span_id=span_id, limit=limit)

    @mcp.tool()
    async def cost_analysis(
        project_id: str | None = None,
        trace_id: str | None = None,
    ) -> str:
        """分析 token 用量与成本：project_id（项目名或 UUID）按项目聚合，trace_id 按轨迹聚合。"""
        return await analyze_cost(sf, project_id=project_id, trace_id=trace_id)

    return mcp


# 模块级实例：供 ``uv run python -m mcp_server.server`` 直接运行。
server = build_server()


def main() -> None:
    """stdio 传输入口。"""
    server.run()


if __name__ == "__main__":
    main()
