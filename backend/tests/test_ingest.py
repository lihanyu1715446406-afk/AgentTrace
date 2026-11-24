"""Ingest 采集写入测试（真实 PostgreSQL 隔离库）：鉴权 + Trace/Span/Token 落库。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.core.exceptions import AuthenticationError
from backend.app.models import Project
from backend.app.repositories import SpanRepository, TokenUsageRepository, TraceRepository
from backend.app.schemas.ingest import SpanIngest, TokenUsageIngest, TraceIngest
from backend.app.services.ingest_service import (
    IngestService,
    hash_api_key,
    verify_api_key,
)


def _payload(project_id: uuid.UUID) -> TraceIngest:
    now = datetime.now(UTC)
    return TraceIngest(
        project_id=project_id,
        trace_id="tr-sdk-001",
        name="SDK 采集诊断",
        status="success",
        started_at=now,
        ended_at=now + timedelta(seconds=2),
        duration_ms=2000,
        spans=[
            SpanIngest(
                span_id="sp-root",
                parent_span_id=None,
                name="llm",
                span_type="llm",
                status="success",
                started_at=now,
                ended_at=now + timedelta(seconds=1),
                duration_ms=1000,
            ),
            SpanIngest(
                span_id="sp-child",
                parent_span_id="sp-root",
                name="tool",
                span_type="tool",
                status="success",
                started_at=now + timedelta(seconds=1),
                ended_at=now + timedelta(seconds=2),
                duration_ms=1000,
            ),
        ],
        token_usages=[
            TokenUsageIngest(
                span_id="sp-root",
                model_name="deepseek-chat",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                estimated_cost=0.0001,
            ),
        ],
    )


async def test_create_project_hashes_key(session_factory):
    async with session_factory() as session:
        service = IngestService(session)
        project_id, raw = await service.create_project("sdk-project")

        project = await session.get(Project, project_id)
        assert project is not None
        assert project.api_key_hash == hash_api_key(raw)
        assert project.api_key_hash != raw
        assert verify_api_key(raw, project.api_key_hash)


async def test_ingest_writes_trace_spans_and_usage(session_factory):
    async with session_factory() as session:
        service = IngestService(session)
        project_id, raw = await service.create_project("sdk-project")
        result = await service.ingest(api_key=raw, payload=_payload(project_id))

        assert result.trace_id == "tr-sdk-001"
        assert result.span_count == 2
        assert result.token_usage_count == 1

    async with session_factory() as session:
        trace = await TraceRepository(session).get_by_trace_id("tr-sdk-001")
        assert trace is not None
        assert trace.name == "SDK 采集诊断"

        spans = await SpanRepository(session).list_by_trace("tr-sdk-001")
        assert len(spans) == 2
        child = next(s for s in spans if s.span_id == "sp-child")
        assert child.parent_span_id == "sp-root"

        usages = await TokenUsageRepository(session).list_by_trace("tr-sdk-001")
        assert len(usages) == 1
        assert usages[0].model_name == "deepseek-chat"
        assert usages[0].total_tokens == 15


async def test_ingest_rejects_bad_api_key(session_factory):
    async with session_factory() as session:
        service = IngestService(session)
        project_id, _ = await service.create_project("sdk-project")
        with pytest.raises(AuthenticationError):
            await service.ingest(api_key="wrong-key", payload=_payload(project_id))


async def test_ingest_rejects_unknown_project(session_factory):
    async with session_factory() as session:
        service = IngestService(session)
        with pytest.raises(AuthenticationError):
            await service.ingest(api_key="whatever", payload=_payload(uuid.uuid4()))
