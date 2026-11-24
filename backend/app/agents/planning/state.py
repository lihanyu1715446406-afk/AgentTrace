"""PlanningAgent 的共享状态（LangGraph State）。"""

import operator
from typing import Annotated, TypedDict

from ...schemas.planning import ExecutionPlan, Intent, StepResult


class AgentState(TypedDict, total=False):
    """Plan-and-Execute 工作流的共享状态。

    - 带 ``Annotated[..., operator.add]`` 的字段：节点返回的值会**追加累积**（而非覆盖）。
    - 其余字段：last-write-wins。

    注意：本文件刻意不使用 ``from __future__ import annotations``，保证 LangGraph
    能直接解析 ``operator.add`` 这个 reducer 对象。
    """

    user_query: str
    task_type: str
    intent: Intent
    execution_plan: ExecutionPlan
    current_step: int
    replan_count: int
    final_report: str
    step_results: Annotated[list[StepResult], operator.add]
