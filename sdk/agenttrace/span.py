"""Span：Trace 中的一个执行单元，支持 token 记录。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any


def _now() -> datetime:
    return datetime.now(UTC)


class Span:
    """一个执行单元（LLM 调用 / 工具调用 / 检索 / 子任务）。

    生命周期由 ``Tracer`` 管理（``start_span`` / ``end_span``），token 记录挂在 Span 上，
    对应数据库 ``TokenUsage``。
    """

    def __init__(
        self,
        *,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        name: str,
        span_type: str,
        input: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.span_id = span_id or uuid.uuid4().hex
        self.parent_span_id = parent_span_id
        self.name = name
        self.span_type = span_type
        self.status = "running"
        self.started_at = _now()
        self.ended_at: datetime | None = None
        self.duration_ms: int | None = None
        self.input = input
        self.output: dict | None = None
        self.error: dict | None = None
        self.metadata = metadata
        self._token_usages: list[dict[str, Any]] = []
        self._context_token: Any = None

    def record_token_usage(
        self,
        *,
        model_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost: float | None = None,
        currency: str = "USD",
    ) -> None:
        """记录一次模型调用的 token 消耗。"""
        self._token_usages.append(
            {
                "span_id": self.span_id,
                "model_name": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": estimated_cost,
                "currency": currency,
            }
        )

    def end(
        self,
        *,
        status: str = "success",
        output: dict | None = None,
        error: dict | None = None,
    ) -> None:
        """结束 Span，记录结束时间、耗时与结果。"""
        self.ended_at = _now()
        self.status = status
        if output is not None:
            self.output = output
        if error is not None:
            self.error = error
        self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)

    def token_usages(self) -> list[dict[str, Any]]:
        return self._token_usages

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_type": self.span_type,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }
