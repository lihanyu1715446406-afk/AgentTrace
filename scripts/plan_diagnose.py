"""M2 演示脚本：PlanningAgent 对不同任务生成计划并按计划执行。

用法（项目根目录）：
    uv run python scripts/seed_demo_data.py
    uv run python scripts/plan_diagnose.py "查询 trace tr-demo-001 的详情"
    uv run python scripts/plan_diagnose.py "demo-project 这个项目花了多少 token？"
    uv run python scripts/plan_diagnose.py "分析一下支付回调为什么失败"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import PlanningAgent  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.tools import ToolRegistry  # noqa: E402


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    query = sys.argv[1] if len(sys.argv) > 1 else "帮我看看 demo-project 有哪些 trace？"
    tools = ToolRegistry(async_session_factory).build_all()
    agent = PlanningAgent(get_llm(), tools)

    print(f"问题：{query}")
    print("-" * 60)
    result = asyncio.run(agent.arun(query))

    print(f"任务类型：{result.task_type}")
    if result.plan:
        print(f"计划概述：{result.plan.summary}")
        for step in result.plan.steps:
            print(
                f"  步骤 {step.step_id}. [{step.tool_name}] {step.description} -> {step.tool_args}"
            )
    print("-" * 60)
    print("执行步骤结果：")
    for r in result.step_results:
        status = "✅" if r.ok else "❌"
        brief = r.output[:120] + ("..." if len(r.output) > 120 else "")
        print(f"  {status} [{r.tool_name}] {brief}")
        if r.error:
            print(f"     错误：{r.error}")
    print("-" * 60)
    print(f"最终报告：\n{result.final_report}")


if __name__ == "__main__":
    main()
