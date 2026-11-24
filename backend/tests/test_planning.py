"""M2 Planning 测试：意图→计划→按计划执行→条件路由→有限重规划。"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from backend.app.agents import PlanningAgent
from backend.app.schemas.planning import ExecutionPlan, Intent, PlanStep, TaskType
from backend.app.tools import ToolRegistry


class _FixedRunnable:
    """返回固定结构化对象的 Runnable 替身。"""

    def __init__(self, output):
        self._output = output

    async def ainvoke(self, *args, **kwargs):
        return self._output


class _PopRunnable:
    """每次调用弹出列表下一个对象的 Runnable 替身（用于重规划返回不同计划）。"""

    def __init__(self, items):
        self._items = items

    async def ainvoke(self, *args, **kwargs):
        return self._items.pop(0)


class FakePlanningLLM:
    """假模型：``with_structured_output`` 返回预设意图/计划，``ainvoke`` 返回预设报告。"""

    def __init__(self, intent, plans, final_report):
        self._intent = intent
        self._plans = plans
        self._final_report = final_report

    def with_structured_output(self, schema, **kwargs):
        if schema is Intent:
            return _FixedRunnable(self._intent)
        if schema is ExecutionPlan:
            return _PopRunnable(self._plans)
        raise AssertionError(f"unexpected schema: {schema}")

    async def ainvoke(self, messages, **kwargs):
        return AIMessage(content=self._final_report)


def _trace_intent(trace_id: str) -> Intent:
    return Intent(
        task_type=TaskType.TRACE_ANALYSIS,
        trace_id=trace_id,
        reasoning="查询单条 trace",
    )


def _trace_step(trace_id: str) -> PlanStep:
    return PlanStep(
        step_id=1,
        description="查 trace",
        tool_name="trace_query",
        tool_args={"trace_id": trace_id},
    )


def _trace_plan(trace_id: str, summary: str) -> ExecutionPlan:
    return ExecutionPlan(
        task_type=TaskType.TRACE_ANALYSIS,
        summary=summary,
        steps=[_trace_step(trace_id)],
    )


async def test_planning_agent_executes_trace_plan(seeded, session_factory):
    plan = _trace_plan(seeded["trace_id"], "查询 trace 详情")
    fake = FakePlanningLLM(_trace_intent(seeded["trace_id"]), [plan], "trace 执行成功。")
    agent = PlanningAgent(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("查询这条 trace 的详情")

    assert result.task_type == "trace_analysis"
    assert result.plan is not None and len(result.plan.steps) == 1
    assert len(result.step_results) == 1
    assert result.step_results[0].ok is True
    assert seeded["trace_id"] in result.step_results[0].output
    assert result.final_report == "trace 执行成功。"


async def test_planning_agent_executes_cost_plan(seeded, session_factory):
    plan = ExecutionPlan(
        task_type=TaskType.COST_ANALYSIS,
        summary="聚合 token 成本",
        steps=[
            PlanStep(
                step_id=1,
                description="聚合成本",
                tool_name="cost_analysis",
                tool_args={"project_id": seeded["project_id"]},
            )
        ],
    )
    fake = FakePlanningLLM(
        Intent(
            task_type=TaskType.COST_ANALYSIS,
            project_id=seeded["project_id"],
            reasoning="成本",
        ),
        [plan],
        "总共 650 token。",
    )
    agent = PlanningAgent(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("这个项目花了多少 token？")

    assert result.task_type == "cost_analysis"
    assert len(result.step_results) == 1
    assert result.step_results[0].ok is True
    assert "650" in result.step_results[0].output


async def test_planning_agent_general_skips_plan_and_tools(session_factory):
    fake = FakePlanningLLM(
        Intent(task_type=TaskType.GENERAL, reasoning="闲聊"),
        [],  # general 不生成计划，不会被消费
        "你好，我是 AgentTrace。",
    )
    agent = PlanningAgent(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("你好")

    assert result.task_type == "general"
    assert result.plan is None
    assert result.step_results == []
    assert result.final_report == "你好，我是 AgentTrace。"


async def test_planning_agent_replans_then_succeeds(seeded, session_factory):
    bad = _trace_plan("nope", "第一次计划（错误 trace_id）")
    good = _trace_plan(seeded["trace_id"], "重规划后的计划")
    fake = FakePlanningLLM(_trace_intent(seeded["trace_id"]), [bad, good], "重规划后成功。")
    agent = PlanningAgent(fake, ToolRegistry(session_factory).build_all())

    result = await agent.arun("查询这条 trace 的详情")

    assert len(result.step_results) == 2
    assert result.step_results[0].ok is False
    assert result.step_results[1].ok is True
    assert seeded["trace_id"] in result.step_results[1].output
    assert result.final_report == "重规划后成功。"


async def test_planning_agent_stops_replanning_at_limit(session_factory):
    bad = _trace_plan("nope", "失败计划")
    fake = FakePlanningLLM(_trace_intent("nope"), [bad, bad, bad, bad], "仍失败。")
    agent = PlanningAgent(fake, ToolRegistry(session_factory).build_all(), max_replan=2)

    result = await agent.arun("查一个不存在的 trace")

    # 1 次原始计划 + 2 次重规划 = 3 次执行，均失败后停止
    assert len(result.step_results) == 3
    assert all(not r.ok for r in result.step_results)
    assert result.final_report == "仍失败。"
