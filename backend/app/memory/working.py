"""WorkingMemory：短期记忆（LangGraph State + Checkpointer），支持中断恢复。

当前任务的临时状态由 LangGraph State + Checkpointer 管理（数据库设计 2.8），不写入
长期记忆表。这里把「诊断 → 人工确认 → 定稿」封装成可中断恢复的工作流，验证 M5
验收项「能恢复中断任务」：第一次 ``start`` 停在人工确认点（``interrupt``），checkpoint
已落盘；第二次 ``resume`` 用同一 ``thread_id`` 从 checkpoint 恢复并完成定稿。
"""

from typing import TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from ..schemas.memory import WorkingSnapshot


class WorkingState(TypedDict, total=False):
    """短期记忆工作流的共享状态（全部 last-write-wins，无 reducer）。"""

    user_query: str
    draft: str
    approved: bool
    final_report: str


class WorkingMemory:
    """带 Checkpointer 的中断恢复工作流。

    节点：``analyze`` → ``confirm``（interrupt）→ ``finalize``。
    ``confirm`` 节点调用 ``interrupt`` 暂停等待人工确认，体现 ADR-0004「外部修改
    Human-in-the-loop」。
    """

    def __init__(
        self, checkpointer: BaseCheckpointSaver, *, llm: BaseChatModel | None = None
    ) -> None:
        self._checkpointer = checkpointer
        self._llm = llm
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(WorkingState)
        graph.add_node("analyze", self._analyze)
        graph.add_node("confirm", self._confirm)
        graph.add_node("finalize", self._finalize)

        graph.add_edge(START, "analyze")
        graph.add_edge("analyze", "confirm")
        graph.add_edge("confirm", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile(checkpointer=self._checkpointer)

    async def _analyze(self, state: WorkingState) -> dict:
        query = state["user_query"]
        if self._llm is not None:
            response = await self._llm.ainvoke(
                [("user", f"请针对以下问题给出初步诊断结论（一段话）：{query}")]
            )
            draft = str(response.content)
        else:
            draft = f"针对「{query}」的初步诊断结论（待人工确认）"
        return {"draft": draft}

    @staticmethod
    def _confirm(state: WorkingState) -> dict:
        approved = interrupt({"question": "是否采纳该诊断结论？", "draft": state.get("draft", "")})
        return {"approved": bool(approved)}

    @staticmethod
    def _finalize(state: WorkingState) -> dict:
        if state.get("approved"):
            report = f"已确认诊断结论：{state.get('draft', '')}"
        else:
            report = "诊断结论未获确认，已终止。"
        return {"final_report": report}

    async def start(self, query: str, thread_id: str) -> WorkingSnapshot:
        """开始一次诊断，运行到人工确认点后暂停（checkpoint 已保存）。"""
        state = await self._graph.ainvoke(
            {"user_query": query}, {"configurable": {"thread_id": thread_id}}
        )
        return self._snapshot(thread_id, state)

    async def resume(self, thread_id: str, approved: bool) -> WorkingSnapshot:
        """从 checkpoint 恢复：传入人工决定，继续执行到定稿。"""
        state = await self._graph.ainvoke(
            Command(resume=approved), {"configurable": {"thread_id": thread_id}}
        )
        return self._snapshot(thread_id, state)

    @staticmethod
    def _snapshot(thread_id: str, state: dict) -> WorkingSnapshot:
        return WorkingSnapshot(
            thread_id=thread_id,
            user_query=state.get("user_query", ""),
            draft=state.get("draft"),
            approved=state.get("approved"),
            final_report=state.get("final_report"),
            interrupted=state.get("final_report") is None,
        )
