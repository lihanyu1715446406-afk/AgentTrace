"""M6 演示脚本：用标准测试集 + LLM-as-judge 评估 PlanningAgent 的效果。

用法（项目根目录，需先 seed 演示数据）：
    uv run python scripts/seed_demo_data.py
    uv run python scripts/eval_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import PlanningAgent  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.evaluation import (  # noqa: E402
    STANDARD_DATASET,
    Evaluator,
    build_llm_judge,
)
from backend.app.schemas.evaluation import CaseOutput, EvalSample  # noqa: E402
from backend.app.tools import ToolRegistry  # noqa: E402


async def _run() -> None:
    llm = get_llm()
    tools = ToolRegistry(async_session_factory).build_all()
    agent = PlanningAgent(llm, tools)

    async def run_case(sample: EvalSample) -> CaseOutput:
        result = await agent.arun(sample.query)
        return CaseOutput(
            task_type=result.task_type,
            tool_names=[s.tool_name for s in result.step_results],
            answer=result.final_report,
        )

    evaluator = Evaluator(judge=build_llm_judge(llm))
    report = await evaluator.evaluate(STANDARD_DATASET, run_case, dataset_name="standard")

    print(f"评估模式：{report.evaluation_mode}")
    print(f"通过 {report.passed}/{report.total}")
    print(f"意图分类准确率：{report.task_type_accuracy}")
    print(f"工具覆盖：{report.tool_coverage}")
    print(f"关键事实覆盖：{report.fact_coverage}")
    print("-" * 60)
    for c in report.cases:
        mark = "通过" if c.passed else "未通过"
        print(f"{mark} {c.sample_id}: task={c.actual_task_type}, tools={c.actual_tool_names}")
    print("-" * 60)
    print(report.summary)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
