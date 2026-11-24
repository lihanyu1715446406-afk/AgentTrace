"""Supervisor：意图分析 + 任务分配决策。"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel

from ...schemas.multi_agent import SupervisorDecision
from ...schemas.planning import Intent, TaskType
from ..planning.intent_analyzer import IntentAnalyzer

_SUPERVISOR_PROMPT = """你是 AgentTrace 的 Supervisor（调度器）。
请根据用户提问，决定需要调度哪些专业分析 Agent 参与。

专业 Agent 角色（role）：
- trace：分析 trace 结构与执行过程（查 trace 详情、span 明细）
- error：分析失败与报错（查 error 状态的 span、failed 的 trace）
- cost：分析 token 用量与成本

用户提问：{query}
已抽取的参数：{intent}

请基于用户提问原文，返回需要调度的角色列表（assigned_roles）。规则：
- 提到 trace 结构/流程 → 包含 "trace"
- 提到成本/token → 包含 "cost"
- 提到报错/失败/异常 → 包含 "error"
- 综合诊断（多个维度都要）→ 列出所有相关角色，例如 ["trace", "error", "cost"]
- 与诊断数据无关的闲聊/问候 → 空列表 []
"""


class Supervisor:
    """M3 的调度器：复用 M2 的意图分析，再用 LLM 决定调度哪些专业 Agent。"""

    def __init__(self, llm: BaseChatModel, intent_analyzer: IntentAnalyzer) -> None:
        self._llm = llm
        self._intent_analyzer = intent_analyzer

    async def __call__(self, state: dict) -> dict:
        query = state["user_query"]
        intent = await self._intent_analyzer.analyze(query)
        decision = await self._decide(query, intent)
        task_type = intent.task_type.value
        if intent.task_type == TaskType.GENERAL and decision.assigned_roles:
            task_type = "comprehensive"
        return {
            "intent": intent,
            "task_type": task_type,
            "assigned_roles": [r.value for r in decision.assigned_roles],
        }

    async def _decide(self, query: str, intent: Intent) -> SupervisorDecision:
        runnable = self._llm.with_structured_output(SupervisorDecision, method="function_calling")
        prompt = _SUPERVISOR_PROMPT.format(
            query=query,
            intent=intent.model_dump(mode="json"),
        )
        return cast(SupervisorDecision, await runnable.ainvoke(prompt))
