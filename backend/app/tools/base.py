"""工具注册中心。"""

from __future__ import annotations

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .cost_tools import build_cost_analysis_tool
from .span_tools import build_span_query_tool
from .trace_tools import build_trace_query_tool


class ToolRegistry:
    """把只读诊断工具绑定到会话工厂并统一注册。

    ``knowledge_tool``（M4）与 ``memory_tool``（M5）都是可选的只读检索工具，不传则
    只注册 M1 的三个 DB 查询工具，保持 M1~M3 的行为不变。
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        knowledge_tool: BaseTool | None = None,
        memory_tool: BaseTool | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._knowledge_tool = knowledge_tool
        self._memory_tool = memory_tool

    def build_all(self) -> list[BaseTool]:
        """返回已注册的全部诊断工具（第一阶段全部只读）。"""
        tools: list[BaseTool] = [
            build_trace_query_tool(self._session_factory),
            build_span_query_tool(self._session_factory),
            build_cost_analysis_tool(self._session_factory),
        ]
        if self._knowledge_tool is not None:
            tools.append(self._knowledge_tool)
        if self._memory_tool is not None:
            tools.append(self._memory_tool)
        return tools
