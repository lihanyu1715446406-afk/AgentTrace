"""写入演示数据，供 M1 单 Agent 查询真实数据。

用法（项目根目录）：
    uv run python scripts/seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

# 让 `python scripts/seed_demo_data.py` 能从项目根目录导入 backend 包（与 alembic/env.py 一致）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.models import Project, Span, TokenUsage, Trace  # noqa: E402
from backend.app.services.ingest_service import hash_api_key  # noqa: E402


async def _seed() -> None:
    async with async_session_factory() as session:
        demo_key = "agt_demo_key"
        existing = await session.execute(select(Project).where(Project.name == "demo-project"))
        existing_project = existing.scalar_one_or_none()
        if existing_project is not None:
            existing_project.api_key_hash = hash_api_key(demo_key)
            await session.commit()
            print("演示数据已存在，已更新其 API Key 哈希。")
            return

        now = datetime.now(UTC)
        project = Project(name="demo-project", api_key_hash=hash_api_key(demo_key))
        session.add(project)
        await session.flush()

        trace_ok = Trace(
            trace_id="tr-demo-001",
            project_id=project.id,
            name="用户登录诊断",
            status="success",
            started_at=now - timedelta(minutes=10),
            ended_at=now - timedelta(minutes=9, seconds=40),
            duration_ms=20_000,
            metadata_={"task_type": "trace_analysis"},
        )
        trace_err = Trace(
            trace_id="tr-demo-002",
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
            span_id="sp-demo-001",
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
        span_tool = Span(
            span_id="sp-demo-002",
            trace_id=trace_ok.trace_id,
            name="trace_query",
            span_type="tool",
            status="success",
            started_at=trace_ok.started_at + timedelta(seconds=15),
            ended_at=trace_ok.ended_at,
            duration_ms=5_000,
            input={"trace_id": trace_ok.trace_id},
            output={"result": "ok"},
        )
        span_err = Span(
            span_id="sp-demo-003",
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
        session.add_all([span_llm, span_tool, span_err])
        await session.flush()

        usage_1 = TokenUsage(
            trace_id=trace_ok.trace_id,
            span_id=span_llm.span_id,
            model_name="deepseek-chat",
            prompt_tokens=120,
            completion_tokens=80,
            total_tokens=200,
            estimated_cost=Decimal("0.0001"),
            currency="USD",
        )
        usage_2 = TokenUsage(
            trace_id=trace_err.trace_id,
            span_id=span_err.span_id,
            model_name="deepseek-chat",
            prompt_tokens=300,
            completion_tokens=150,
            total_tokens=450,
            estimated_cost=Decimal("0.0002"),
            currency="USD",
        )
        session.add_all([usage_1, usage_2])
        await session.commit()

    print("演示数据写入完成：demo-project，2 条 trace，3 条 span，2 条 token 用量。")
    print(f"Demo API Key（Trace 浏览器中填写）：{demo_key}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
