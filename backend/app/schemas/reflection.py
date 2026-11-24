"""Reflection（反思/自省）相关的 Pydantic 数据模型：证据检查 + 一致性检查 + 有限重分析。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .multi_agent import SupervisorResult


class EvidenceStatus(StrEnum):
    """单条诊断结论的证据支撑状态。"""

    SUPPORTED = "supported"  # 有工具数据支撑
    MISSING = "missing"  # 缺证据：结论找不到对应数据
    CONTRADICTED = "contradicted"  # 与工具数据矛盾
    UNVERIFIABLE = "unverifiable"  # 数据维度无关，无法验证


class ClaimCheck(BaseModel):
    """单条结论的证据检查结果。"""

    claim: str = Field(description="被检查的结论句")
    status: EvidenceStatus = Field(description="证据支撑状态")
    evidence: str = Field(default="", description="支撑/矛盾的证据摘要（缺证据时为空）")
    reason: str = Field(default="", description="一句话判定理由")


class ConsistencyIssue(BaseModel):
    """一条一致性（自相矛盾）问题。"""

    description: str = Field(description="矛盾点描述")
    claims: list[str] = Field(default_factory=list, description="相互矛盾的结论句")


class ReflectionResult(BaseModel):
    """一次反思的结构化结果。"""

    query: str
    source_report: str = Field(description="被反思的原始诊断报告")
    claims: list[ClaimCheck] = Field(default_factory=list, description="逐条结论的证据检查结果")
    consistency_issues: list[ConsistencyIssue] = Field(
        default_factory=list, description="结论间的一致性问题"
    )
    needs_reanalysis: bool = Field(
        default=False, description="是否存在缺证据/矛盾结论，需要触发一次重分析"
    )
    iteration: int = Field(default=0, description="第几轮反思（0 起）")


class ReflectiveResult(BaseModel):
    """有限重分析循环的最终结果。"""

    query: str
    final_result: SupervisorResult = Field(description="最后一轮（重）分析得到的诊断结果")
    reflections: list[ReflectionResult] = Field(
        default_factory=list, description="每一轮的反思记录（第一轮为初始分析）"
    )
    iterations: int = Field(default=0, description="实际发生的重分析轮数")
