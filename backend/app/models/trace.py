"""Trace 与 Span 模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin


class Trace(Base, UUIDPrimaryKeyMixin):
    """一次完整的 Agent 任务执行过程。"""

    __tablename__ = "traces"

    trace_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    # 注意：`metadata` 是 SQLAlchemy 保留属性名，列名仍为 metadata，属性名用 metadata_。
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    spans: Mapped[list[Span]] = relationship(back_populates="trace")


class Span(Base, UUIDPrimaryKeyMixin):
    """Trace 中的一个执行单元（LLM 调用 / 工具调用 / 推理 / 检索 / 子任务）。"""

    __tablename__ = "spans"

    span_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    trace_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("traces.trace_id"), nullable=False, index=True
    )
    parent_span_id: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    span_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    input: Mapped[dict | None] = mapped_column(JSONB)
    output: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    trace: Mapped[Trace] = relationship(back_populates="spans")
