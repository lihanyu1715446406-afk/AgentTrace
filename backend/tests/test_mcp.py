"""MCP Server 测试：只读诊断工具实现 + MCPServer 注册。"""

from __future__ import annotations

import json

from mcp_server.server import analyze_cost, build_server, query_span, query_trace


async def test_query_trace_by_id(seeded, session_factory):
    data = json.loads(await query_trace(session_factory, trace_id=seeded["trace_id"]))
    assert data["trace"]["trace_id"] == seeded["trace_id"]
    assert data["trace"]["status"] == "success"


async def test_query_trace_by_project(seeded, session_factory):
    data = json.loads(await query_trace(session_factory, project_id=seeded["project_id"]))
    assert len(data["traces"]) == 2


async def test_query_trace_by_project_name(seeded, session_factory):
    data = json.loads(await query_trace(session_factory, project_id=seeded["project_name"]))
    assert len(data["traces"]) == 2


async def test_query_trace_unknown_project_name_returns_error(seeded, session_factory):
    data = json.loads(await query_trace(session_factory, project_id="不存在的项目"))
    assert "error" in data


async def test_query_span_by_trace(seeded, session_factory):
    data = json.loads(await query_span(session_factory, trace_id=seeded["trace_id"]))
    assert len(data["spans"]) == 1
    assert data["spans"][0]["span_id"] == seeded["span_id"]


async def test_analyze_cost_by_trace(seeded, session_factory):
    data = json.loads(await analyze_cost(session_factory, trace_id=seeded["trace_id"]))
    assert data["cost"]["total_tokens"] == 200


async def test_analyze_cost_by_project_name(seeded, session_factory):
    data = json.loads(await analyze_cost(session_factory, project_id=seeded["project_name"]))
    assert data["cost"]["total_tokens"] == 650


async def test_build_server_registers_readonly_tools(session_factory):
    server = build_server(session_factory)
    tools = await server.list_tools()
    names = {tool.name for tool in tools}
    assert names == {"trace_query", "span_query", "cost_analysis"}
