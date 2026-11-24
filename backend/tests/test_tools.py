"""工具层测试：三个只读工具对真实数据返回正确 JSON。"""

from __future__ import annotations

import json

from backend.app.tools import ToolRegistry


def _get_tool(session_factory, name: str):
    tools = ToolRegistry(session_factory).build_all()
    return next(t for t in tools if t.name == name)


async def test_trace_query_tool_by_trace_id(seeded, session_factory):
    tool = _get_tool(session_factory, "trace_query")
    data = json.loads(await tool.ainvoke({"trace_id": seeded["trace_id"]}))
    assert data["trace"]["trace_id"] == seeded["trace_id"]
    assert data["trace"]["status"] == "success"


async def test_trace_query_tool_by_project(seeded, session_factory):
    tool = _get_tool(session_factory, "trace_query")
    data = json.loads(await tool.ainvoke({"project_id": seeded["project_id"]}))
    assert len(data["traces"]) == 2


async def test_trace_query_tool_by_project_name(seeded, session_factory):
    tool = _get_tool(session_factory, "trace_query")
    data = json.loads(await tool.ainvoke({"project_id": seeded["project_name"]}))
    assert len(data["traces"]) == 2


async def test_trace_query_tool_unknown_project_name_returns_error(seeded, session_factory):
    tool = _get_tool(session_factory, "trace_query")
    data = json.loads(await tool.ainvoke({"project_id": "不存在的项目"}))
    assert "error" in data


async def test_trace_query_tool_missing_returns_error(seeded, session_factory):
    tool = _get_tool(session_factory, "trace_query")
    data = json.loads(await tool.ainvoke({"trace_id": "nope"}))
    assert "error" in data


async def test_span_query_tool_by_trace_id(seeded, session_factory):
    tool = _get_tool(session_factory, "span_query")
    data = json.loads(await tool.ainvoke({"trace_id": seeded["trace_id"]}))
    assert len(data["spans"]) == 1
    assert data["spans"][0]["span_type"] == "llm"


async def test_span_query_tool_by_span_id(seeded, session_factory):
    tool = _get_tool(session_factory, "span_query")
    data = json.loads(await tool.ainvoke({"span_id": seeded["span_id"]}))
    assert data["span"]["span_id"] == seeded["span_id"]


async def test_cost_analysis_tool_by_project(seeded, session_factory):
    tool = _get_tool(session_factory, "cost_analysis")
    data = json.loads(await tool.ainvoke({"project_id": seeded["project_id"]}))
    assert data["cost"]["total_tokens"] == 650
    assert data["cost"]["total_cost"] is not None


async def test_cost_analysis_tool_by_project_name(seeded, session_factory):
    tool = _get_tool(session_factory, "cost_analysis")
    data = json.loads(await tool.ainvoke({"project_id": seeded["project_name"]}))
    assert data["cost"]["total_tokens"] == 650
