"""意图分析器：把自然语言提问归类为诊断任务类型并抽取参数。"""

from __future__ import annotations

from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel

from ...schemas.planning import Intent

_INTENT_PROMPT = """你是 AgentTrace 诊断平台的意图分析器。请判断用户的诊断任务类型，并抽取关键参数。

任务类型（task_type）：
- trace_analysis：查询某条 trace 详情，或列出某项目下的 trace
- error_analysis：分析失败/报错的 trace 或 span（含「失败」「错误」「异常」「超时」等意图）
- cost_analysis：分析 token 用量与成本
- general：与诊断数据无关的闲聊或无法判断

用户提问：{query}

请返回：task_type、trace_id（若用户提到，否则省略）、project_id（若用户提到，否则省略）、
reasoning（一句话分类依据）。
"""


class IntentAnalyzer:
    """用 LLM 结构化输出完成意图分类与参数抽取。"""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def analyze(self, query: str) -> Intent:
        """分析提问，返回结构化的 ``Intent``。"""
        runnable = self._llm.with_structured_output(Intent, method="function_calling")
        return cast(Intent, await runnable.ainvoke(_INTENT_PROMPT.format(query=query)))
