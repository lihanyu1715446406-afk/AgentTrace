"""Report Agent：汇总各专业 Agent 的分析结果，生成统一报告。"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

_REPORT_PROMPT = """你是 AgentTrace 的 Report Agent。
请汇总多个专业 Agent 的分析结果，生成一份统一诊断报告。

用户提问：{query}
任务类型：{task_type}
各 Agent 分析结果：
{analysis_results}

要求：
- 用简洁的 Markdown 组织报告；
- 结论必须来自上面的分析结果，不要编造数据；
- 如果某个分析结果为空或含 error，如实说明；
- 多个维度（trace/error/cost）分别成节，最后给出综合结论；
- 如果未调用任何专业 Agent（分析结果为空），直接礼貌回答用户提问即可，不必生成诊断报告。
"""


class ReportAgent:
    """汇总 ``analysis_results``，生成最终报告。"""

    def __init__(self, llm: BaseChatModel) -> None:
        self._llm = llm

    async def __call__(self, state: dict) -> dict:
        return {"final_report": await self._synthesize(state)}

    async def _synthesize(self, state: dict) -> str:
        results = state.get("analysis_results", [])
        if not results:
            lines = "（本次未调用任何专业分析 Agent）"
        else:
            lines = "\n".join(
                f"- [{r.role}] {r.summary}\n  发现：{'; '.join(r.findings) or '无'}"
                for r in results
            )
        prompt = _REPORT_PROMPT.format(
            query=state["user_query"],
            task_type=state.get("task_type", ""),
            analysis_results=lines,
        )
        response = await self._llm.ainvoke([("user", prompt)])
        return str(response.content)
