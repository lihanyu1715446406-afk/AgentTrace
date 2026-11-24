"""pytest 全局夹具：使用隔离的 agenttrace_test PostgreSQL 库。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings
from backend.app.models import Base, Project, Span, TokenUsage, Trace

TEST_DB_NAME = "agenttrace_test"


def _database_url(db: str) -> str:
    s = get_settings()
    return (
        f"postgresql+asyncpg://{s.postgres_user}:{s.postgres_password}"
        f"@{s.postgres_host}:{s.postgres_port}/{db}"
    )


async def _ensure_test_database() -> None:
    """确保 agenttrace_test 库存在（连接 postgres 维护库判断/创建）。"""
    admin = create_async_engine(_database_url("postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        await admin.dispose()


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """每个测试使用全新 schema 的会话工厂（drop + create 保证隔离）。"""
    await _ensure_test_database()
    engine = create_async_engine(_database_url(TEST_DB_NAME))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.fixture
async def seeded(session_factory) -> AsyncIterator[dict]:
    """写入并提交一组演示数据，返回可用的 id。"""
    async with session_factory() as session:
        ids = await _seed(session)
        await session.commit()
    yield ids


async def _seed(session: AsyncSession) -> dict:
    now = datetime.now(UTC)
    project = Project(name="test-project", api_key_hash="test-hash")
    session.add(project)
    await session.flush()

    trace_ok = Trace(
        trace_id="tr-test-001",
        project_id=project.id,
        name="登录链路诊断",
        status="success",
        started_at=now - timedelta(minutes=10),
        ended_at=now - timedelta(minutes=9, seconds=40),
        duration_ms=20_000,
        metadata_={"task_type": "trace_analysis"},
    )
    trace_err = Trace(
        trace_id="tr-test-002",
        project_id=project.id,
        name="支付回调诊断",
        status="failed",
        started_at=now - timedelta(minutes=5),
        ended_at=now - timedelta(minutes=4, seconds=30),
        duration_ms=30_000,
        metadata_={"task_type": "error_analysis"},
    )
    session.add_all([trace_ok, trace_err])
    await session.flush()

    span_llm = Span(
        span_id="sp-test-001",
        trace_id=trace_ok.trace_id,
        name="llm_call",
        span_type="llm",
        status="success",
        started_at=trace_ok.started_at,
        ended_at=trace_ok.started_at + timedelta(seconds=15),
        duration_ms=15_000,
        input={"prompt": "分析登录链路"},
        output={"content": "无异常"},
    )
    span_err = Span(
        span_id="sp-test-002",
        trace_id=trace_err.trace_id,
        name="llm_call",
        span_type="llm",
        status="error",
        started_at=trace_err.started_at,
        ended_at=trace_err.ended_at,
        duration_ms=30_000,
        input={"prompt": "分析支付回调"},
        error={"message": "上游超时"},
    )
    session.add_all([span_llm, span_err])
    await session.flush()

    usage_ok = TokenUsage(
        trace_id=trace_ok.trace_id,
        span_id=span_llm.span_id,
        model_name="deepseek-chat",
        prompt_tokens=120,
        completion_tokens=80,
        total_tokens=200,
        estimated_cost=Decimal("0.0001"),
        currency="USD",
    )
    usage_err = TokenUsage(
        trace_id=trace_err.trace_id,
        span_id=span_err.span_id,
        model_name="deepseek-chat",
        prompt_tokens=300,
        completion_tokens=150,
        total_tokens=450,
        estimated_cost=Decimal("0.0002"),
        currency="USD",
    )
    session.add_all([usage_ok, usage_err])
    await session.flush()

    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "trace_id": trace_ok.trace_id,
        "failed_trace_id": trace_err.trace_id,
        "span_id": span_llm.span_id,
        "failed_span_id": span_err.span_id,
    }
