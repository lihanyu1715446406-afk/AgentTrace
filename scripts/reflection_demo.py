"""M6 演示脚本：反思（证据检查 + 一致性检查）+ 有限重分析。

用法（项目根目录，需先 seed 演示数据）：
    uv run python scripts/seed_demo_data.py
    uv run python scripts/reflection_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import MultiAgentOrchestrator  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.reflection import ReflectiveDiagnoser, Reflector  # noqa: E402
from backend.app.tools import ToolRegistry  # noqa: E402


async def _run() -> None:
    llm = get_llm()
    tools = ToolRegistry(async_session_factory).build_all()
    orchestrator = MultiAgentOrchestrator(llm, tools)
    reflective = ReflectiveDiagnoser(orchestrator.arun, Reflector(llm=llm), max_reflections=2)

    query = "分析 tr-demo-002 为什么失败，并评估它的 token 成本"
    result = await reflective.arun(query)

    print(f"问题：{query}")
    print(f"重分析轮数：{result.iterations}")
    print("-" * 60)
    for i, r in enumerate(result.reflections):
        print(f"[第 {i} 轮反思] needs_reanalysis={r.needs_reanalysis}")
        for c in r.claims:
            print(f"  [{c.status.value}] {c.claim}")
            if c.reason:
                print(f"      理由：{c.reason}")
        for issue in r.consistency_issues:
            print(f"  [矛盾] {issue.description}")
    print("-" * 60)
    print(f"最终报告：\n{result.final_result.final_report}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
