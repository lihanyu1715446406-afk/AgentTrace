"""ReflectiveDiagnoser：诊断 → 反思 → 有限重分析 的自省循环。

验收项「有限重分析」：首轮诊断后反思，若存在缺证据/矛盾结论，把反馈注入 query 触发
重新诊断，最多 ``max_reflections`` 轮，避免无限循环。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..schemas.multi_agent import SupervisorResult
from ..schemas.reflection import EvidenceStatus, ReflectionResult, ReflectiveResult
from .reflector import Reflector

# 诊断函数：给定 query，返回一次多 Agent 诊断结果。
type DiagnoseFunc = Callable[[str], Awaitable[SupervisorResult]]


class ReflectiveDiagnoser:
    """包装一个诊断函数，加入反思与有限重分析。"""

    def __init__(
        self,
        diagnose: DiagnoseFunc,
        reflector: Reflector,
        *,
        max_reflections: int = 2,
    ) -> None:
        self._diagnose = diagnose
        self._reflector = reflector
        self._max_reflections = max_reflections

    async def arun(self, query: str) -> ReflectiveResult:
        """诊断并反思，缺证据/矛盾时有限重分析。"""
        result = await self._diagnose(query)
        reflections: list[ReflectionResult] = [await self._reflector.reflect(result, iteration=0)]

        while reflections[-1].needs_reanalysis and len(reflections) - 1 < self._max_reflections:
            feedback = self._build_feedback(reflections[-1])
            result = await self._diagnose(f"{query}\n\n（反思补充要求）{feedback}")
            reflections.append(await self._reflector.reflect(result, iteration=len(reflections)))

        return ReflectiveResult(
            query=query,
            final_result=result,
            reflections=reflections,
            iterations=len(reflections) - 1,
        )

    @staticmethod
    def _build_feedback(reflection: ReflectionResult) -> str:
        """把反思结果转成可供下一轮诊断参考的补充要求。"""
        parts: list[str] = []
        missing = [c.claim for c in reflection.claims if c.status == EvidenceStatus.MISSING]
        contradicted = [
            c.claim for c in reflection.claims if c.status == EvidenceStatus.CONTRADICTED
        ]
        if missing:
            parts.append("以下结论缺证据，请补充工具数据后重新给出：\n- " + "\n- ".join(missing))
        if contradicted:
            parts.append("以下结论与工具数据矛盾，请修正：\n- " + "\n- ".join(contradicted))
        if reflection.consistency_issues:
            parts.append(
                "以下结论互相矛盾，请消除矛盾：\n- "
                + "\n- ".join(i.description for i in reflection.consistency_issues)
            )
        return "\n".join(parts)
