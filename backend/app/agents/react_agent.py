"""基于 LangGraph 的单 Agent（ReAct + Tool Calling）。"""

from __future__ import annotations

from typing import Any, cast

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..schemas import AgentResult, ToolCallRecord


class DiagnoseAgent:
    """M1 的单 Agent：接收自然语言提问，自主选择只读工具取真实数据并作答。"""

    def __init__(self, llm: BaseChatModel, tools: list[BaseTool]) -> None:
        self._llm = llm
        self._tools = tools
        self._agent = create_agent(self._llm, self._tools)

    def run(self, query: str) -> AgentResult:
        """同步执行一次诊断。"""
        state = self._agent.invoke(cast(Any, {"messages": [("user", query)]}))
        return self._build_result(query, state["messages"])

    async def arun(self, query: str) -> AgentResult:
        """异步执行一次诊断。"""
        state = await self._agent.ainvoke(cast(Any, {"messages": [("user", query)]}))
        return self._build_result(query, state["messages"])

    @staticmethod
    def _build_result(query: str, messages: list[BaseMessage]) -> AgentResult:
        # 1) 收集 ToolMessage 的输出，按 tool_call_id 建立索引。
        tool_outputs: dict[str, str] = {}
        for message in messages:
            if isinstance(message, ToolMessage):
                tool_outputs[message.tool_call_id] = str(message.content)

        # 2) 遍历 AIMessage 中的 tool_calls，生成工具调用记录。
        tool_calls: list[ToolCallRecord] = []
        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                for call in message.tool_calls:
                    tool_calls.append(
                        ToolCallRecord(
                            tool_name=call["name"],
                            args=call["args"],
                            output=tool_outputs.get(call["id"] or "", ""),
                        )
                    )

        # 3) 取最后一条带正文的 AIMessage 作为最终回答。
        answer = ""
        for message in reversed(messages):
            if isinstance(message, AIMessage) and message.content:
                answer = str(message.content)
                break

        return AgentResult(query=query, answer=answer, tool_calls=tool_calls)
