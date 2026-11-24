"""Multi-Agent Orchestrator：Supervisor + 专业 Agent + Report Agent 的编排。"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from ...schemas.multi_agent import SupervisorResult
from ..planning.intent_analyzer import IntentAnalyzer
from .analyzers import CostAnalyzer, ErrorAnalyzer, TraceAnalyzer
from .report_agent import ReportAgent
from .state import MultiAgentState
from .supervisor import Supervisor


class MultiAgentOrchestrator:
    """M3 的 Multi-Agent 编排器。

    图结构：
        START → supervisor ─(Send 动态并行)→ trace/error/cost analyzer ─→ report → END

    - 条件路由：Supervisor 按任务决定 ``assigned_roles``，只调度相关 Agent。
    - 并行执行：多个角色用 ``Send`` 动态 fan-out，并行产出 ``analysis_results``。
    - 顺序执行：Report Agent 在所有分析完成后汇总（``analysis_results`` 用 reducer 累加）。
    """

    def __init__(self, llm: BaseChatModel, tools: list[BaseTool]) -> None:
        self._supervisor = Supervisor(llm, IntentAnalyzer(llm))
        self._analyzers = {
            "trace_analyzer": TraceAnalyzer(llm, tools),
            "error_analyzer": ErrorAnalyzer(llm, tools),
            "cost_analyzer": CostAnalyzer(llm, tools),
        }
        self._report = ReportAgent(llm)
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(MultiAgentState)
        graph.add_node("supervisor", self._supervisor)
        graph.add_node("trace_analyzer", self._analyzers["trace_analyzer"])
        graph.add_node("error_analyzer", self._analyzers["error_analyzer"])
        graph.add_node("cost_analyzer", self._analyzers["cost_analyzer"])
        graph.add_node("report", self._report)

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._dispatch,
            ["trace_analyzer", "error_analyzer", "cost_analyzer", "report"],
        )
        graph.add_edge("trace_analyzer", "report")
        graph.add_edge("error_analyzer", "report")
        graph.add_edge("cost_analyzer", "report")
        graph.add_edge("report", END)
        return graph.compile()

    def _dispatch(self, state: dict):
        """把 Supervisor 选定的角色 fan-out 成并行 Send；无角色则直接进 report。"""
        roles = state.get("assigned_roles", [])
        if not roles:
            return "report"
        payload = {"user_query": state["user_query"], "intent": state["intent"]}
        return [Send(f"{role}_analyzer", payload) for role in roles]

    async def arun(self, query: str) -> SupervisorResult:
        state = await self._graph.ainvoke({"user_query": query})
        return self._build_result(query, state)

    def run(self, query: str) -> SupervisorResult:
        state = self._graph.invoke({"user_query": query})
        return self._build_result(query, state)

    @staticmethod
    def _build_result(query: str, state: MultiAgentState) -> SupervisorResult:
        return SupervisorResult(
            query=query,
            task_type=state.get("task_type"),
            assigned_roles=list(state.get("assigned_roles", [])),
            analysis_results=list(state.get("analysis_results", [])),
            final_report=state.get("final_report", ""),
        )
