"""Planning 相关的 Pydantic 数据模型（意图、计划、步骤、执行结果）。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TaskType(StrEnum):
    """诊断任务类型。"""

    TRACE_ANALYSIS = "trace_analysis"
    ERROR_ANALYSIS = "error_analysis"
    COST_ANALYSIS = "cost_analysis"
    GENERAL = "general"


class Intent(BaseModel):
    """意图分析结果：任务类型 + 关键参数。"""

    task_type: TaskType = Field(description="诊断任务类型")
    trace_id: str | None = Field(default=None, description="用户提到的 trace_id")
    project_id: str | None = Field(default=None, description="用户提到的项目 ID（UUID 字符串）")
    reasoning: str = Field(default="", description="分类依据，一句话说明")


class PlanStep(BaseModel):
    """执行计划中的一步：调用哪个只读工具、传什么参数。"""

    step_id: int = Field(description="步骤序号，从 1 开始")
    description: str = Field(description="这一步要做什么")
    tool_name: str = Field(description="要调用的工具：trace_query / span_query / cost_analysis")
    tool_args: dict = Field(default_factory=dict, description="工具入参")


class ExecutionPlan(BaseModel):
    """结构化执行计划。"""

    task_type: TaskType = Field(description="计划对应的任务类型")
    summary: str = Field(description="计划概述，一句话")
    steps: list[PlanStep] = Field(description="按依赖顺序排列的执行步骤")


class StepResult(BaseModel):
    """单个计划步骤的执行结果。"""

    step_id: int
    tool_name: str
    ok: bool
    output: str
    error: str | None = None


class PlanResult(BaseModel):
    """PlanningAgent 一次诊断的结构化结果。"""

    query: str
    task_type: str | None
    plan: ExecutionPlan | None
    step_results: list[StepResult]
    final_report: str
