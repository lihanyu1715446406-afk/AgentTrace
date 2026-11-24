"""Multi-Agent（M3）的共享状态（LangGraph State）。"""

import operator
from typing import Annotated, TypedDict

from ...schemas.multi_agent import AnalysisResult
from ...schemas.planning import Intent


class MultiAgentState(TypedDict, total=False):
    """Supervisor + 专业 Agent 的共享状态。

    - ``analysis_results`` 用 ``operator.add`` reducer：多个并行 Agent 的结果会追加累积。
    - 其余字段 last-write-wins。

    注意：刻意不写 ``from __future__ import annotations``，保证 LangGraph
    能在运行时解析 ``operator.add`` 这个 reducer 对象。
    """

    user_query: str
    task_type: str
    intent: Intent
    assigned_roles: list[str]
    analysis_results: Annotated[list[AnalysisResult], operator.add]
    final_report: str
