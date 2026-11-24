"""专业分析 Agent：Trace / Error / Cost 三个 Analyzer。"""

from __future__ import annotations

import json
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from ...schemas.multi_agent import AnalysisDraft, AnalysisResult, AnalyzerRole
from ...schemas.planning import Intent

_TRACE_PROMPT = """你是 Trace 结构分析专家。根据工具返回的数据，总结 trace 的结构与执行过程。

用户提问：{query}
工具数据：
{data}

请给出 summary（一句话结论）和 findings（若干发现点）。只依据工具数据，不要编造。
"""

_ERROR_PROMPT = """你是错误分析专家。根据工具返回的 trace/span 数据，识别失败与报错。

用户提问：{query}
工具数据：
{data}

请给出 summary（一句话结论）和 findings（若干发现点，重点指出哪些 span/trace 出错、
错误信息、可能原因）。只依据工具数据，不要编造。
"""

_COST_PROMPT = """你是成本分析专家。根据工具返回的成本聚合数据，总结 token 用量与成本。

用户提问：{query}
工具数据：
{data}

请给出 summary（一句话结论）和 findings（若干发现点，重点指出总 token、总成本、按模型分项）。
只依据工具数据，不要编造。
"""


class _BaseAnalyzer:
    """专业 Analyzer 基类：调只读工具取数 → LLM 提炼 → 组装结构化 AnalysisResult。"""

    role: AnalyzerRole
    prompt: str

    def __init__(self, llm: BaseChatModel, tools: list[BaseTool]) -> None:
        self._llm = llm
        self._tools_by_name = {t.name: t for t in tools}

    async def _call_tool(self, name: str, args: dict) -> dict:
        tool = self._tools_by_name[name]
        raw = await tool.ainvoke(args)
        return json.loads(str(raw))

    async def _draft(self, query: str, data: dict) -> AnalysisDraft:
        runnable = self._llm.with_structured_output(AnalysisDraft, method="function_calling")
        prompt = self.prompt.format(query=query, data=json.dumps(data, ensure_ascii=False))
        return cast(AnalysisDraft, await runnable.ainvoke(prompt))

    async def __call__(self, state: dict) -> dict:
        data = await self.collect(state["intent"])
        draft = await self._draft(state["user_query"], data)
        result = AnalysisResult(
            role=self.role.value,
            summary=draft.summary,
            findings=draft.findings,
            data=data,
        )
        return {"analysis_results": [result]}

    async def collect(self, intent: Intent) -> dict:
        raise NotImplementedError


class TraceAnalyzer(_BaseAnalyzer):
    """分析 trace 结构与执行过程。"""

    role = AnalyzerRole.TRACE
    prompt = _TRACE_PROMPT

    async def collect(self, intent: Intent) -> dict:
        data: dict = {}
        if intent.trace_id:
            data.update(await self._call_tool("trace_query", {"trace_id": intent.trace_id}))
            data.update(await self._call_tool("span_query", {"trace_id": intent.trace_id}))
        elif intent.project_id:
            data.update(await self._call_tool("trace_query", {"project_id": intent.project_id}))
        return data


class ErrorAnalyzer(_BaseAnalyzer):
    """分析失败与报错。"""

    role = AnalyzerRole.ERROR
    prompt = _ERROR_PROMPT

    async def collect(self, intent: Intent) -> dict:
        if intent.trace_id:
            return await self._call_tool("span_query", {"trace_id": intent.trace_id})
        if intent.project_id:
            return await self._call_tool("trace_query", {"project_id": intent.project_id})
        return {}


class CostAnalyzer(_BaseAnalyzer):
    """分析 token 用量与成本。"""

    role = AnalyzerRole.COST
    prompt = _COST_PROMPT

    async def collect(self, intent: Intent) -> dict:
        if intent.trace_id:
            return await self._call_tool("cost_analysis", {"trace_id": intent.trace_id})
        if intent.project_id:
            return await self._call_tool("cost_analysis", {"project_id": intent.project_id})
        return {}
