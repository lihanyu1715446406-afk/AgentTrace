"""Trace：一次完整 Agent 任务执行过程，聚合 spans 与 token 用量。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from .span import Span


def _now() -> datetime:
    return datetime.now(UTC)


class Trace:
    """一次 Agent 任务执行，对应数据库 ``Trace``。"""

    def __init__(
        self,
        *,
        trace_id: str | None = None,
        name: str,
        project_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.trace_id = trace_id or uuid.uuid4().hex
        self.name = name
        self.project_id = project_id
        self.status = "running"
        self.started_at = _now()
        self.ended_at: datetime | None = None
        self.duration_ms: int | None = None
        self.metadata = metadata
        self.spans: list[Span] = []
        self._context_token: Any = None

    def end(self, *, status: str = "success") -> None:
        """结束 Trace，记录结束时间与耗时。"""
        self.ended_at = _now()
        self.status = status
        self.duration_ms = int((self.ended_at - self.started_at).total_seconds() * 1000)

    def token_usages(self) -> list[dict[str, Any]]:
        """汇总所有 Span 的 token 用量。"""
        usages: list[dict[str, Any]] = []
        for span in self.spans:
            usages.extend(span.token_usages())
        return usages

    def to_payload(self, project_id: str) -> dict[str, Any]:
        """序列化为上报 body（时间转 ISO 字符串，字段与后端 TraceIngest 对齐）。"""
        return {
            "project_id": project_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "spans": [s.to_dict() for s in self.spans],
            "token_usages": self.token_usages(),
        }
