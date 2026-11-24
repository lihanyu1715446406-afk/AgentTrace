"""M5 演示脚本：长期记忆（写入/去重/检索/巩固）+ Agent 检索历史经历。

用法（项目根目录，需设置 DEEPSEEK_API_KEY）：
    uv run python scripts/memory_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import DiagnoseAgent  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.memory import MemoryManager  # noqa: E402
from backend.app.models import Project  # noqa: E402
from backend.app.schemas.memory import MemoryType  # noqa: E402
from backend.app.tools import ToolRegistry, build_memory_search_tool  # noqa: E402

_PROJECT_NAME = "demo-project"


async def _ensure_project() -> str:
    """幂等创建一个演示项目，返回其 UUID 字符串。"""
    async with async_session_factory() as session:
        result = await session.execute(select(Project).where(Project.name == _PROJECT_NAME))
        project = result.scalar_one_or_none()
        if project is None:
            project = Project(name=_PROJECT_NAME, api_key_hash="demo-hash-not-a-real-key")
            session.add(project)
            await session.commit()
            await session.refresh(project)
        return str(project.id)


async def _run() -> None:
    pid = await _ensure_project()
    manager = MemoryManager(async_session_factory, llm=get_llm())

    # 1) 写入情景记忆（重复写入同一内容会被去重更新，而非新增）
    print("== 写入情景记忆 ==")
    for content in [
        "支付回调 span 报 error：上游超时，耗时接近阈值，判断为下游响应慢",
        "登录链路诊断：某次因网络抖动导致上游超时，耗时不长却超时",
        "成本分析：某项目 total_tokens 突增，因上下文未裁剪",
    ]:
        r = await manager.record(pid, MemoryType.EPISODIC, content)
        action = "新建" if r.created else "去重更新"
        print(f"  [{action}] {r.memory_type} {content[:24]}...")

    # 2) 检索历史经历
    print("\n== 检索关键词『超时』 ==")
    hits = await manager.recall(pid, "超时")
    print(f"  命中 {len(hits.hits)} 条：")
    for h in hits.hits:
        print(f"  - [{h.memory_type}] {h.content}")

    # 3) 巩固：把情景记忆提炼成语义记忆
    print("\n== 记忆巩固（episodic → semantic） ==")
    consolidation = await manager.consolidate(pid)
    if consolidation.semantic_memory is not None:
        print(f"  语义记忆：{consolidation.semantic_memory.content}")
    else:
        print(f"  跳过：{consolidation.skipped_reason}")

    # 4) Agent 通过 memory_search 工具检索历史经历
    print("\n== Agent 检索历史经历 ==")
    memory_tool = build_memory_search_tool(manager)
    tools = ToolRegistry(async_session_factory, memory_tool=memory_tool).build_all()
    agent = DiagnoseAgent(get_llm(), tools)
    query = "这次的问题之前遇到过吗？请在历史记忆里查找和上游超时相关的经历。"
    result = await agent.arun(query)
    print(f"  回答：{result.answer}")
    if result.tool_calls:
        print("  工具调用：")
        for call in result.tool_calls:
            print(f"    * {call.tool_name}({call.args})")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
