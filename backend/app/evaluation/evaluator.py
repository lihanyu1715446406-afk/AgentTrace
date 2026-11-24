"""Evaluator：用标准测试集评估诊断 Agent 的效果，产出评估报告。

指标：意图分类准确率（task_type_accuracy）、工具覆盖（tool_coverage）、关键事实覆盖
（fact_coverage）、综合通过（passed）。默认用精确匹配（子串/集合），注入 ``judge`` 则切换为
LLM-as-a-Judge（语义判定替代事实子串匹配）。``run_case`` 把一条样本跑成标准化 ``CaseOutput``，
使评估逻辑与具体 Agent 解耦。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from ..schemas.evaluation import (
    CaseOutput,
    EvalCaseResult,
    EvalReport,
    EvalSample,
)

# run_case：跑一条样本，返回标准化输出。
type RunCase = Callable[[EvalSample], Awaitable[CaseOutput]]
# judge：LLM-as-judge，判定答案是否满足样本要求。
type CaseJudge = Callable[[EvalSample, CaseOutput], Awaitable[bool]]

_JUDGE_PROMPT = """你是 AgentTrace 的评估裁判（LLM-as-a-Judge）。判断诊断 Agent 的回答
是否满足用户问题。

用户问题：{query}
期望任务类型：{expected_task_type}
关键事实（参考）：{expected_facts}
黄金答案（参考）：{golden_answer}

Agent 回答：
{answer}

只判断「回答是否正确且完整地解决了问题」，返回 pass（是/否）与 reason（一句话）。
"""


class _JudgeVerdict(BaseModel):
    """LLM 对答案是否合格的判定。"""

    pass_: bool = Field(alias="pass", description="答案是否合格")
    reason: str = ""


def build_llm_judge(llm: BaseChatModel) -> CaseJudge:
    """构建 LLM-as-a-Judge：用 LLM 判定答案是否满足样本要求。"""

    async def _judge(sample: EvalSample, output: CaseOutput) -> bool:
        runnable = llm.with_structured_output(_JudgeVerdict, method="function_calling")
        prompt = _JUDGE_PROMPT.format(
            query=sample.query,
            expected_task_type=sample.expected_task_type or "（未指定）",
            expected_facts="、".join(sample.expected_facts) or "（未指定）",
            golden_answer=sample.golden_answer or "（未指定）",
            answer=output.answer,
        )
        verdict = cast(_JudgeVerdict, await runnable.ainvoke(prompt))
        return verdict.pass_

    return _judge


class Evaluator:
    """跑标准测试集，逐样本评分并汇总为评估报告。"""

    def __init__(self, *, judge: CaseJudge | None = None) -> None:
        self._judge = judge

    async def evaluate(
        self,
        dataset: list[EvalSample],
        run_case: RunCase,
        *,
        dataset_name: str = "standard",
    ) -> EvalReport:
        """逐样本运行并评分，返回整体报告。"""
        cases = [await self._score(sample, await run_case(sample)) for sample in dataset]

        total = len(cases)
        passed = sum(1 for c in cases if c.passed)
        fact_covered = sum(c.facts_covered for c in cases)
        fact_total = sum(c.facts_total for c in cases)

        return EvalReport(
            dataset_name=dataset_name,
            evaluation_mode="llm_judge" if self._judge else "deterministic",
            total=total,
            passed=passed,
            task_type_accuracy=self._ratio(sum(1 for c in cases if c.task_type_match), total),
            tool_coverage=self._ratio(sum(1 for c in cases if c.tool_match), total),
            fact_coverage=self._ratio(fact_covered, fact_total),
            cases=cases,
            summary=self._summarize(cases, total, passed, fact_covered, fact_total),
        )

    async def _score(self, sample: EvalSample, output: CaseOutput) -> EvalCaseResult:
        task_type_match = output.task_type == sample.expected_task_type
        tool_match = set(sample.expected_tool_names) <= set(output.tool_names)

        answer_lower = output.answer.lower()
        facts_covered = sum(1 for f in sample.expected_facts if f.lower() in answer_lower)
        facts_total = len(sample.expected_facts)

        if self._judge is not None:
            # LLM-as-judge：语义判定替代事实子串匹配，避免措辞差异导致的假阴性。
            passed = task_type_match and tool_match and await self._judge(sample, output)
        else:
            passed = (
                task_type_match
                and tool_match
                and (facts_covered == facts_total if facts_total else True)
            )

        return EvalCaseResult(
            sample_id=sample.sample_id,
            actual_task_type=output.task_type,
            actual_tool_names=output.tool_names,
            actual_answer=output.answer,
            task_type_match=task_type_match,
            tool_match=tool_match,
            facts_covered=facts_covered,
            facts_total=facts_total,
            passed=passed,
        )

    @staticmethod
    def _ratio(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    @staticmethod
    def _summarize(
        cases: list[EvalCaseResult],
        total: int,
        passed: int,
        fact_covered: int,
        fact_total: int,
    ) -> str:
        failed = [c.sample_id for c in cases if not c.passed]
        return (
            f"共 {total} 条样本，通过 {passed} 条；"
            f"关键事实覆盖 {fact_covered}/{fact_total}；"
            f"未通过样本：{', '.join(failed) if failed else '无'}。"
        )
