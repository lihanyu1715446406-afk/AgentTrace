"""Reflector：对诊断结果做证据检查 + 一致性检查（反思/自省）。

验收项「能识别缺证据的结论」：把 M3 的 ``SupervisorResult`` 中每条结论（summary/finding）
与真实工具数据（``analysis_results[].data``）逐条比对，判定 evidence status；再检查结论之间
是否自相矛盾。LLM 判断通过 ``judge`` / ``consistency_checker`` 注入点隔离，测试用确定性 fake。
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import cast

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from ..schemas.multi_agent import SupervisorResult
from ..schemas.reflection import (
    ClaimCheck,
    ConsistencyIssue,
    EvidenceStatus,
    ReflectionResult,
)

# judge：给定结论句与证据（JSON 字符串），返回证据支撑状态。
type ClaimJudge = Callable[[str, str], Awaitable[EvidenceStatus]]
# consistency_checker：给定结论句列表，返回一致性问题列表。
type ConsistencyChecker = Callable[[list[str]], Awaitable[list[ConsistencyIssue]]]

_CLAIM_PROMPT = """你是 AgentTrace 的证据审查员。判断下面这条诊断结论是否被工具数据支撑。

结论：{claim}
工具数据：{evidence}

只依据工具数据判断，返回：
- status：supported（有数据支撑）/ missing（结论找不到对应数据，缺证据）/
  contradicted（与数据矛盾）/ unverifiable（数据维度无关、无法验证）
- evidence：支撑或矛盾的证据原文摘要（missing 时留空）
- reason：一句话判定理由
"""

_CONSISTENCY_PROMPT = """你是 AgentTrace 的一致性审查员。判断下面的诊断结论之间是否存在互相矛盾。

结论列表：
{claims}

只返回互相矛盾的结论组（description 描述矛盾点，claims 列出矛盾结论）。若无矛盾返回空 issues 列表。
"""


class _ClaimVerdict(BaseModel):
    """LLM 对单条结论的证据判定（claim 由代码填充）。"""

    status: EvidenceStatus
    evidence: str = ""
    reason: str = ""


class _ConsistencyVerdict(BaseModel):
    """LLM 对结论列表的一致性判定。"""

    issues: list[ConsistencyIssue] = Field(default_factory=list)


class Reflector:
    """对一次多 Agent 诊断结果做反思：证据检查 + 一致性检查。

    - ``judge`` / ``consistency_checker`` 为注入点；不注入则用 LLM（``with_structured_output``）。
    - 证据检查是核心（验收项）；一致性检查可选（无 LLM 且无注入时跳过）。
    """

    def __init__(
        self,
        *,
        llm: BaseChatModel | None = None,
        judge: ClaimJudge | None = None,
        consistency_checker: ConsistencyChecker | None = None,
    ) -> None:
        self._llm = llm
        self._judge = judge
        self._consistency_checker = consistency_checker

    async def reflect(self, result: SupervisorResult, *, iteration: int = 0) -> ReflectionResult:
        """反思一次诊断结果，返回逐条结论的证据检查 + 一致性问题。"""
        claims: list[ClaimCheck] = []
        for analysis in result.analysis_results:
            evidence = json.dumps(analysis.data, ensure_ascii=False)
            # summary 作为一条结论；每条 finding 各作为一条结论。
            claims.append(await self._check(f"[{analysis.role}] {analysis.summary}", evidence))
            for finding in analysis.findings:
                claims.append(await self._check(finding, evidence))

        issues = await self._check_consistency([c.claim for c in claims])

        needs_reanalysis = any(
            c.status in (EvidenceStatus.MISSING, EvidenceStatus.CONTRADICTED) for c in claims
        ) or bool(issues)

        return ReflectionResult(
            query=result.query,
            source_report=result.final_report,
            claims=claims,
            consistency_issues=issues,
            needs_reanalysis=needs_reanalysis,
            iteration=iteration,
        )

    async def _check(self, claim: str, evidence: str) -> ClaimCheck:
        if self._judge is not None:
            status = await self._judge(claim, evidence)
            return ClaimCheck(claim=claim, status=status)
        if self._llm is None:
            raise ValueError("Reflector 需要注入 LLM 或 judge 函数")
        runnable = self._llm.with_structured_output(_ClaimVerdict, method="function_calling")
        verdict = cast(
            _ClaimVerdict,
            await runnable.ainvoke(_CLAIM_PROMPT.format(claim=claim, evidence=evidence)),
        )
        return ClaimCheck(
            claim=claim,
            status=verdict.status,
            evidence=verdict.evidence,
            reason=verdict.reason,
        )

    async def _check_consistency(self, claims: list[str]) -> list[ConsistencyIssue]:
        if self._consistency_checker is not None:
            return await self._consistency_checker(claims)
        if self._llm is None or not claims:
            return []
        runnable = self._llm.with_structured_output(_ConsistencyVerdict, method="function_calling")
        body = "\n".join(f"- {c}" for c in claims)
        verdict = cast(
            _ConsistencyVerdict,
            await runnable.ainvoke(_CONSISTENCY_PROMPT.format(claims=body)),
        )
        return verdict.issues
