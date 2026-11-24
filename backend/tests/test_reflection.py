"""M6 Reflection 测试：证据检查、一致性检查、有限重分析。

Reflector 的 LLM 判断通过 ``judge`` / ``consistency_checker`` 注入确定性 fake，不依赖真实 LLM。
"""

from __future__ import annotations

from backend.app.reflection import ReflectiveDiagnoser, Reflector
from backend.app.schemas.multi_agent import AnalysisResult, SupervisorResult
from backend.app.schemas.reflection import ConsistencyIssue, EvidenceStatus

_MISSING = "根因是数据库连接池耗尽"


def _result(
    summary: str = "登录链路执行正常",
    findings: list[str] | None = None,
    *,
    data: dict | None = None,
) -> SupervisorResult:
    return SupervisorResult(
        query="诊断登录链路",
        task_type="trace_analysis",
        assigned_roles=["trace"],
        analysis_results=[
            AnalysisResult(
                role="trace",
                summary=summary,
                findings=findings or [],
                data=data or {"trace": {"status": "success"}},
            )
        ],
        final_report="登录链路执行正常，无异常。",
    )


async def _mixed_judge(claim: str, evidence: str) -> EvidenceStatus:
    if _MISSING in claim:
        return EvidenceStatus.MISSING
    return EvidenceStatus.SUPPORTED


async def _supported_judge(claim: str, evidence: str) -> EvidenceStatus:
    return EvidenceStatus.SUPPORTED


async def test_reflector_marks_missing_evidence() -> None:
    reflector = Reflector(judge=_mixed_judge)
    reflection = await reflector.reflect(_result(findings=[_MISSING]))
    assert EvidenceStatus.MISSING in {c.status for c in reflection.claims}
    assert reflection.needs_reanalysis is True


async def test_reflector_supported_no_reanalysis() -> None:
    reflector = Reflector(judge=_supported_judge)
    reflection = await reflector.reflect(_result(findings=["执行耗时 20 秒"]))
    assert all(c.status == EvidenceStatus.SUPPORTED for c in reflection.claims)
    assert reflection.needs_reanalysis is False


async def test_reflector_consistency_conflict() -> None:
    async def checker(claims: list[str]) -> list[ConsistencyIssue]:
        return [ConsistencyIssue(description="登录链路既成功又失败", claims=claims)]

    reflector = Reflector(judge=_supported_judge, consistency_checker=checker)
    reflection = await reflector.reflect(_result())
    assert len(reflection.consistency_issues) == 1
    assert reflection.needs_reanalysis is True


async def test_reflective_no_reanalysis() -> None:
    async def diagnose(query: str) -> SupervisorResult:
        return _result()

    agent = ReflectiveDiagnoser(diagnose, Reflector(judge=_supported_judge))
    result = await agent.arun("诊断登录链路")
    assert result.iterations == 0
    assert len(result.reflections) == 1


async def test_reflective_reanalysis_fixes_evidence() -> None:
    calls = {"n": 0}

    async def diagnose(query: str) -> SupervisorResult:
        calls["n"] += 1
        if calls["n"] == 1:
            return _result(findings=[_MISSING])
        return _result(findings=["根因是上游超时"])

    agent = ReflectiveDiagnoser(diagnose, Reflector(judge=_mixed_judge))
    result = await agent.arun("诊断登录链路")
    assert result.iterations == 1
    assert calls["n"] == 2
    assert result.final_result.analysis_results[0].findings == ["根因是上游超时"]


async def test_reflective_max_reflections_bound() -> None:
    async def diagnose(query: str) -> SupervisorResult:
        return _result(findings=[_MISSING])

    agent = ReflectiveDiagnoser(diagnose, Reflector(judge=_mixed_judge), max_reflections=2)
    result = await agent.arun("诊断登录链路")
    assert result.iterations == 2
    assert len(result.reflections) == 3
