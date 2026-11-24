"""M7 演示脚本：外部 Python Agent 通过 SDK 采集并异步上报，再查询展示真实数据。

用法（项目根目录，需先 seed 演示数据 + 配置 DeepSeek）：
    uv run python scripts/seed_demo_data.py
    uv run python scripts/sdk_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from langchain.agents import create_agent  # noqa: E402

from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.tools import ToolRegistry  # noqa: E402
from sdk.agenttrace import AgentTraceClient, TraceCallbackHandler, Tracer  # noqa: E402


def _print_trace(detail: dict) -> None:
    trace = detail["trace"]
    print(
        f"Trace: {trace['trace_id']}  名称={trace['name']}  "
        f"状态={trace['status']}  耗时={trace['duration_ms']}ms"
    )
    for span in detail["spans"]:
        parent = span["parent_span_id"] or "（根）"
        print(
            f"  Span: {span['span_id']}  parent={parent}  "
            f"type={span['span_type']}  name={span['name']}"
        )
    for usage in detail["token_usages"]:
        print(
            f"  Token: {usage['model_name']}  prompt={usage['prompt_tokens']}  "
            f"completion={usage['completion_tokens']}  total={usage['total_tokens']}"
        )


async def _run() -> None:
    transport = ASGITransport(app=app)

    # 1. 创建接入项目，拿到 project_id 与一次性 API Key。
    async with AsyncClient(transport=transport, base_url="http://agenttrace") as c:
        resp = await c.post("/projects", json={"name": "sdk-demo-project"})
        resp.raise_for_status()
        created = resp.json()

    project_id = created["project_id"]
    api_key = created["api_key"]
    print(f"已创建接入项目：{created['name']}（project_id={project_id}）")
    print(f"API Key（仅此一次返回）：{api_key}")

    # 2. 用 SDK 客户端 + Tracer 采集一个真实 LangGraph Agent 的执行。
    client = AgentTraceClient(
        endpoint="http://agenttrace",
        api_key=api_key,
        project_id=project_id,
        transport=transport,
    )
    tracer = Tracer(client)
    handler = TraceCallbackHandler(tracer)

    llm = get_llm()
    tools = ToolRegistry(async_session_factory).build_all()
    agent = create_agent(llm, tools)

    query = "查询 trace tr-demo-001 的详细信息"
    print(f"\n外部 Agent 问题：{query}")

    with tracer.trace("外部 Agent 登录链路诊断") as trace:
        with tracer.span("agent_run", span_type="chain"):
            result = await agent.ainvoke(
                cast(Any, {"messages": [("user", query)]}),
                config={"callbacks": [handler]},
            )

    print(f"Agent 回答：{str(result['messages'][-1].content)}")

    # 3. 异步上报，再查询展示真实采集数据。
    receipt = await client.flush(trace)
    print(f"\n上报回执：{receipt}")

    detail = await client.get_trace(trace.trace_id)
    print("\n===== 从后端查询到的真实采集数据 =====")
    _print_trace(detail)

    traces = await client.list_traces()
    print(f"\n本项目已采集 Trace 数：{len(traces)}")
    for t in traces:
        print(f"  - {t['trace_id']}  {t['name']}  {t['status']}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
