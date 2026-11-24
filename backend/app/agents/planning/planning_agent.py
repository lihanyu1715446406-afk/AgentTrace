"""Plan-and-Execute 诊断 Agent：意图 → 计划 → 按计划执行 → 有限重规划 → 汇总。"""

from __future__ import annotations

import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph

from ...schemas.planning import (
    ExecutionPlan,
    Intent,
    PlanResult,
    PlanStep,
    StepResult,
    TaskType,
)
from .intent_analyzer import IntentAnalyzer
from .state import AgentState
from .task_planner import TaskPlanner

_SYNTHESIZE_PROMPT = """你是 AgentTrace 诊断平台的报告生成器。
请根据工具执行结果，回答用户的问题，给出有据可查的结论。

用户提问：{query}
任务类型：{task_type}
执行结果：
{step_results}

要求：
- 用简洁的 Markdown 组织回答；
- 结论必须来自上面的执行结果，不要编造数据；
- 如果结果中有 error 或未找到数据，如实说明，不要臆测。
"""


class PlanningAgent:
    """M2 的 Plan-and-Execute Agent：LLM 生成计划，按计划调用只读工具执行。

    图结构：
        START → analyze_intent ─┬─(general)──────────────┐
                                 └─(plan) → generate_plan ┴→ execute_step ⇄ replan
        → finalize → END
    """

    def __init__(self, llm: BaseChatModel, tools: list[BaseTool], *, max_replan: int = 3) -> None:
        self._llm = llm
        self._tools_by_name = {t.name: t for t in tools}
        self._intent_analyzer = IntentAnalyzer(llm)
        self._task_planner = TaskPlanner(llm)
        self._max_replan = max_replan
        self._graph = self._build_graph()

    # ---- 图构建 ----
    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("analyze_intent", self._analyze_intent)
        graph.add_node("generate_plan", self._generate_plan)
        graph.add_node("execute_step", self._execute_step)
        graph.add_node("replan", self._replan)
        graph.add_node("finalize", self._finalize)

        graph.add_edge(START, "analyze_intent")
        graph.add_conditional_edges(
            "analyze_intent",
            self._route_after_intent,
            {"plan": "generate_plan", "finalize": "finalize"},
        )
        graph.add_conditional_edges(
            "generate_plan",
            self._route_after_plan,
            {"execute": "execute_step", "finalize": "finalize"},
        )
        graph.add_conditional_edges(
            "execute_step",
            self._route_after_step,
            {"execute": "execute_step", "replan": "replan", "finalize": "finalize"},
        )
        graph.add_conditional_edges(
            "replan",
            self._route_after_replan,
            {"execute": "execute_step", "finalize": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    # ---- 节点 ----
    async def _analyze_intent(self, state: AgentState) -> dict:
        intent = await self._intent_analyzer.analyze(state["user_query"])
        return {"intent": intent, "task_type": intent.task_type.value}

    async def _generate_plan(self, state: AgentState) -> dict:
        plan = await self._task_planner.plan(state["user_query"], state["intent"])
        return {"execution_plan": plan, "current_step": 0}

    async def _execute_step(self, state: AgentState) -> dict:
        plan: ExecutionPlan = state["execution_plan"]
        idx = state.get("current_step", 0)
        step: PlanStep = plan.steps[idx]

        tool = self._tools_by_name.get(step.tool_name)
        if tool is None:
            result = StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                ok=False,
                output="",
                error=f"未知工具：{step.tool_name}",
            )
            return {"step_results": [result], "current_step": idx + 1}

        try:
            output_str = str(await tool.ainvoke(step.tool_args))
            data = json.loads(output_str)
            has_error = isinstance(data, dict) and "error" in data
            result = StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                ok=not has_error,
                output=output_str,
                error=data.get("error") if has_error else None,
            )
        except Exception as exc:  # 工具异常不中断图，而是进入有限重规划
            result = StepResult(
                step_id=step.step_id,
                tool_name=step.tool_name,
                ok=False,
                output="",
                error=str(exc),
            )
        return {"step_results": [result], "current_step": idx + 1}

    async def _replan(self, state: AgentState) -> dict:
        last = state["step_results"][-1]
        context = f"上一步「{last.tool_name}」执行失败：{last.error or '未找到数据'}。请调整计划。"
        plan = await self._task_planner.plan(state["user_query"], state["intent"], context=context)
        return {
            "execution_plan": plan,
            "current_step": 0,
            "replan_count": state.get("replan_count", 0) + 1,
        }

    async def _finalize(self, state: AgentState) -> dict:
        return {"final_report": await self._synthesize(state)}

    async def _synthesize(self, state: AgentState) -> str:
        lines = [
            f"- [{r.tool_name}] {'ok' if r.ok else 'error'}: {r.output or r.error}"
            for r in state.get("step_results", [])
        ]
        step_results = "\n".join(lines) or "（本次未调用任何工具）"
        prompt = _SYNTHESIZE_PROMPT.format(
            query=state["user_query"],
            task_type=state.get("task_type", ""),
            step_results=step_results,
        )
        response = await self._llm.ainvoke([("user", prompt)])
        return str(response.content)

    # ---- 条件路由 ----
    def _route_after_intent(self, state: AgentState) -> str:
        intent: Intent = state["intent"]
        return "finalize" if intent.task_type == TaskType.GENERAL else "plan"

    def _route_after_plan(self, state: AgentState) -> str:
        return "execute" if state["execution_plan"].steps else "finalize"

    def _route_after_step(self, state: AgentState) -> str:
        last = state["step_results"][-1] if state.get("step_results") else None
        if last is not None and not last.ok:
            if state.get("replan_count", 0) < self._max_replan:
                return "replan"
        if state.get("current_step", 0) < len(state["execution_plan"].steps):
            return "execute"
        return "finalize"

    def _route_after_replan(self, state: AgentState) -> str:
        return "execute" if state["execution_plan"].steps else "finalize"

    # ---- 对外接口 ----
    async def arun(self, query: str) -> PlanResult:
        state = await self._graph.ainvoke({"user_query": query})
        return self._build_result(query, state)

    def run(self, query: str) -> PlanResult:
        state = self._graph.invoke({"user_query": query})
        return self._build_result(query, state)

    @staticmethod
    def _build_result(query: str, state: AgentState) -> PlanResult:
        return PlanResult(
            query=query,
            task_type=state.get("task_type"),
            plan=state.get("execution_plan"),
            step_results=list(state.get("step_results", [])),
            final_report=state.get("final_report", ""),
        )
