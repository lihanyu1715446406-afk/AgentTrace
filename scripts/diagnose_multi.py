"""M3 演示脚本：MultiAgentOrchestrator 一次综合诊断调度多个专业 Agent。

用法（项目根目录）：
    uv run python scripts/seed_demo_data.py
    uv run python scripts/diagnose_multi.py "全面分析 demo-project 的健康状况"
    uv run python scripts/diagnose_multi.py "tr-demo-002 为什么失败？"
    uv run python scripts/diagnose_multi.py "tr-demo-001 花了多少 token？"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import MultiAgentOrchestrator  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.tools import ToolRegistry  # noqa: E402


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    query = sys.argv[1] if len(sys.argv) > 1 else "全面分析 demo-project 的健康状况"
    tools = ToolRegistry(async_session_factory).build_all()
    agent = MultiAgentOrchestrator(get_llm(), tools)

    print(f"问题：{query}")
    print("-" * 60)
    result = asyncio.run(agent.arun(query))

    print(f"任务类型：{result.task_type}")
    print(f"调度的 Agent：{result.assigned_roles}")
    print("-" * 60)
    print("各 Agent 分析结果：")
    for r in result.analysis_results:
        print(f"  [{r.role}] {r.summary}")
        for finding in r.findings:
            print(f"      - {finding}")
    print("-" * 60)
    print(f"最终报告：\n{result.final_report}")


if __name__ == "__main__":
    main()
