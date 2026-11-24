"""仓库层只读查询测试（真实 PostgreSQL 隔离库）。"""

from __future__ import annotations

import uuid

from backend.app.repositories import (
    SpanRepository,
    TokenUsageRepository,
    TraceRepository,
)


async def test_trace_repository_get_by_trace_id(seeded, session_factory):
    async with session_factory() as session:
        repo = TraceRepository(session)
        trace = await repo.get_by_trace_id(seeded["trace_id"])
        assert trace is not None
        assert trace.name == "登录链路诊断"
        assert trace.status == "success"


async def test_trace_repository_get_missing_returns_none(seeded, session_factory):
    async with session_factory() as session:
        repo = TraceRepository(session)
        assert await repo.get_by_trace_id("does-not-exist") is None


async def test_trace_repository_list_by_project(seeded, session_factory):
    async with session_factory() as session:
        repo = TraceRepository(session)
        traces = await repo.list_by_project(uuid.UUID(seeded["project_id"]))
        trace_ids = {t.trace_id for t in traces}
        assert len(traces) == 2
        assert seeded["trace_id"] in trace_ids
        assert seeded["failed_trace_id"] in trace_ids


async def test_span_repository_list_by_trace(seeded, session_factory):
    async with session_factory() as session:
        repo = SpanRepository(session)
        spans = await repo.list_by_trace(seeded["trace_id"])
        assert len(spans) == 1
        assert spans[0].span_type == "llm"


async def test_token_usage_aggregate_by_project(seeded, session_factory):
    async with session_factory() as session:
        repo = TokenUsageRepository(session)
        summary = await repo.aggregate_by_project(uuid.UUID(seeded["project_id"]))
        assert summary["total_tokens"] == 650  # 200 + 450
        assert len(summary["by_model"]) == 1
        assert summary["by_model"][0]["model_name"] == "deepseek-chat"
        assert summary["total_cost"] is not None


async def test_token_usage_aggregate_by_trace(seeded, session_factory):
    async with session_factory() as session:
        repo = TokenUsageRepository(session)
        summary = await repo.aggregate_by_trace(seeded["trace_id"])
        assert summary["total_tokens"] == 200
