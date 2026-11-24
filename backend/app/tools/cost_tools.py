"""成本分析工具（只读）。"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories import ProjectRepository, TokenUsageRepository
from ..schemas import CostSummary


class CostAnalysisInput(BaseModel):
    """cost_analysis 工具入参。"""

    project_id: str | None = Field(
        default=None, description="按项目聚合成本（项目名或 UUID 字符串）"
    )
    trace_id: str | None = Field(default=None, description="按单条轨迹聚合成本")


def build_cost_analysis_tool(
    session_factory: async_sessionmaker[AsyncSession],
) -> StructuredTool:
    """构建 CostAnalysisTool：按项目或轨迹聚合 token 用量与成本。"""

    async def _analyze(project_id: str | None = None, trace_id: str | None = None) -> str:
        if not project_id and not trace_id:
            return json.dumps({"error": "必须提供 project_id 或 trace_id 之一"}, ensure_ascii=False)

        async with session_factory() as session:
            repo = TokenUsageRepository(session)
            if project_id:
                pid = await ProjectRepository(session).resolve(project_id)
                if pid is None:
                    return json.dumps(
                        {"error": f"未找到项目：{project_id}（支持项目名或 UUID）"},
                        ensure_ascii=False,
                    )
                summary = await repo.aggregate_by_project(pid)
            elif trace_id:
                summary = await repo.aggregate_by_trace(trace_id)
            else:  # 防御性兜底，正常不会到达
                return json.dumps(
                    {"error": "必须提供 project_id 或 trace_id 之一"}, ensure_ascii=False
                )

            return json.dumps(
                {"cost": CostSummary(**summary).model_dump(mode="json")},
                ensure_ascii=False,
            )

    return StructuredTool.from_function(
        name="cost_analysis",
        description=(
            "分析 Token 用量与成本。提供 project_id（项目名或 UUID）时按项目聚合；"
            "提供 trace_id 时按单条轨迹聚合。返回总 token 数、总成本与按模型的分项。"
        ),
        args_schema=CostAnalysisInput,
        coroutine=_analyze,
    )
