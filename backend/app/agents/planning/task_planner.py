"""任务规划器：根据意图生成结构化的分步执行计划。"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel

from ...schemas.planning import ExecutionPlan, Intent

_PLAN_PROMPT = """你是 AgentTrace 诊断平台的计划生成器。
请根据用户意图，生成一个由若干步骤组成的执行计划。

可用工具（全部只读）：
- trace_query：查询 trace。入参 trace_id（查单条）或 project_id（列列表）、limit（可选，默认 10）。
- span_query：查询 span。入参 span_id（查单条）或 trace_id（查该 trace 下全部 span）、
  limit（可选）。
- cost_analysis：成本分析。入参 project_id（按项目聚合）或 trace_id（按单条聚合）。

用户提问：{query}
任务类型：{task_type}
意图参数：{intent}
{context}

请生成执行计划：每步必须指定 tool_name（三者之一）和 tool_args；步骤按依赖顺序
（先查 trace，再查其 span，最后做成本汇总）；步骤数量不要超过 5。
"""


class TaskPlanner:
    """用 LLM 结构化输出生成执行计划。"""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def plan(self, query: str, intent: Intent, *, context: str = "") -> ExecutionPlan:
        """根据意图生成 ``ExecutionPlan``；``context`` 用于重规划时携带失败原因。"""
        runnable = self._llm.with_structured_output(ExecutionPlan, method="function_calling")
        prompt = _PLAN_PROMPT.format(
            query=query,
            task_type=intent.task_type.value,
            intent=intent.model_dump(mode="json"),
            context=f"补充信息：{context}" if context else "",
        )
        return cast(ExecutionPlan, await runnable.ainvoke(prompt))
