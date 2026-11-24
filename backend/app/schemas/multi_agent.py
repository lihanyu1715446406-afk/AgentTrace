"""Multi-Agent（M3）相关的 Pydantic 数据模型。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AnalyzerRole(StrEnum):
    """专业分析 Agent 的角色。"""

    TRACE = "trace"
    ERROR = "error"
    COST = "cost"


class AnalysisResult(BaseModel):
    """单个专业 Agent 的结构化分析产出。"""

    role: str = Field(description="产出该结果的 Agent 角色")
    summary: str = Field(description="该维度的分析结论，一句话")
    findings: list[str] = Field(default_factory=list, description="发现点列表")
    data: dict = Field(default_factory=dict, description="支撑结论的工具原始数据")
    error: str | None = Field(default=None, description="该分析失败时的错误信息")


class AnalysisDraft(BaseModel):
    """LLM 基于工具数据生成的「分析草稿」，仅含 summary 与 findings。

    设计：role 与 data 由 Analyzer 代码组装（保证角色正确、数据真实），
    只有 summary / findings 交给 LLM 生成。
    """

    summary: str = Field(description="分析结论，一句话")
    findings: list[str] = Field(default_factory=list, description="发现点列表")


class SupervisorDecision(BaseModel):
    """Supervisor 的任务分配决策。"""

    assigned_roles: list[AnalyzerRole] = Field(description="需要调度的专业 Agent 角色")
    reasoning: str = Field(default="", description="分配依据，一句话")


class SupervisorResult(BaseModel):
    """Multi-Agent 一次综合诊断的结构化结果。"""

    query: str
    task_type: str | None
    assigned_roles: list[str]
    analysis_results: list[AnalysisResult]
    final_report: str
