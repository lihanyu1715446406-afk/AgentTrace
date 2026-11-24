"""M3 Multi-Agent 测试：Supervisor 调度、并行协作、条件路由、统一报告。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from backend.app.agents import MultiAgentOrchestrator
from backend.app.schemas.multi_agent import (
    AnalysisDraft,
    AnalyzerRole,
    SupervisorDecision,
)
from backend.app.schemas.planning import Intent, TaskType
from backend.app.tools import ToolRegistry


class _FixedRunnable:
    """返回固定对象的 Runnable 替身。"""

    def __init__(self, output):
        self._output = output

    async def ainvoke(self, *args, **kwargs):
        return self._output


class _PopRunnable:
    """每次调用弹出列表下一个对象的 Runnable 替身（供多个 Analyzer 依次取草稿）。"""

    def __init__(self, items):
        self._items = list(items)

    async def ainvoke(self, *args, **kwargs):
        return self._items.pop(0)


class FakeMultiLLM:
    """假模型：按 schema 类型返回固定意图/决策/分析草稿，``ainvoke`` 返回固定报告。"""

    def __init__(self, intent, decision, drafts, report):
        self._intent = intent
        self._decision = decision
        self._drafts = list(drafts)
        self._report = report

    def with_structured_output(self, schema, **kwargs):
        if schema is Intent:
            return _FixedRunnable(self._intent)
        if schema is SupervisorDecision:
            return _FixedRunnable(self._decision)
        if schema is AnalysisDraft:
            return _PopRunnable(self._drafts)
        raise AssertionError(f"unexpected schema: {schema}")

    async def ainvoke(self, messages, **kwargs):
        return AIMessage(content=self._report)


def _draft(summary: str, *findings: str) -> AnalysisDraft:
    return AnalysisDraft(summary=summary, findings=list(findings))


async def test_comprehensive_parallel_analysis(seeded, session_factory):
    fake = FakeMultiLLM(
        Intent(task_type=TaskType.TRACE_ANALYSIS, trace_id=seeded["trace_id"]),
        SupervisorDecision(
            assigned_roles=[AnalyzerRole.TRACE, AnalyzerRole.ERROR, AnalyzerRole.COST],
            reasoning="综合诊断",
        ),
        [
            _draft("trace 结构正常", "含 1 个 span"),
            _draft("未发现错误", "无 error span"),
            _draft("成本 200 token", "total_tokens=200"),
        ],
        "统一诊断报告。",
    )
    agent = MultiAgentOrchestrator(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("全面分析这条 trace")

    assert result.task_type == "trace_analysis"
    assert result.assigned_roles == ["trace", "error", "cost"]
    assert len(result.analysis_results) == 3
    by_role = {r.role: r for r in result.analysis_results}
    assert set(by_role) == {"trace", "error", "cost"}
    # 数据来自真实工具返回（非 LLM 编造）
    assert "trace" in by_role["trace"].data
    assert "spans" in by_role["trace"].data
    assert "spans" in by_role["error"].data
    assert "cost" in by_role["cost"].data
    assert result.final_report == "统一诊断报告。"


async def test_cost_task_only_routes_to_cost_analyzer(seeded, session_factory):
    fake = FakeMultiLLM(
        Intent(task_type=TaskType.COST_ANALYSIS, project_id=seeded["project_id"]),
        SupervisorDecision(assigned_roles=[AnalyzerRole.COST], reasoning="只查成本"),
        [_draft("总成本 650 token", "total_tokens=650")],
        "成本报告。",
    )
    agent = MultiAgentOrchestrator(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("这个项目花了多少 token？")

    assert result.task_type == "cost_analysis"
    assert result.assigned_roles == ["cost"]
    assert len(result.analysis_results) == 1
    assert result.analysis_results[0].role == "cost"
    assert "cost" in result.analysis_results[0].data


async def test_error_task_routes_to_error_analyzer(seeded, session_factory):
    fake = FakeMultiLLM(
        Intent(task_type=TaskType.ERROR_ANALYSIS, trace_id=seeded["failed_trace_id"]),
        SupervisorDecision(assigned_roles=[AnalyzerRole.ERROR], reasoning="查失败原因"),
        [_draft("存在 error span", "上游超时")],
        "错误报告。",
    )
    agent = MultiAgentOrchestrator(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("这条 trace 为什么失败？")

    assert result.task_type == "error_analysis"
    assert result.assigned_roles == ["error"]
    assert len(result.analysis_results) == 1
    assert result.analysis_results[0].role == "error"
    assert "spans" in result.analysis_results[0].data


async def test_general_skips_analyzers(session_factory):
    fake = FakeMultiLLM(
        Intent(task_type=TaskType.GENERAL, reasoning="闲聊"),
        SupervisorDecision(assigned_roles=[], reasoning=""),
        [],
        "你好，我是 AgentTrace。",
    )
    agent = MultiAgentOrchestrator(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("你好")

    assert result.task_type == "general"
    assert result.assigned_roles == []
    assert result.analysis_results == []
    assert result.final_report == "你好，我是 AgentTrace。"
