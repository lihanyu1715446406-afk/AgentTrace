"""采集上下文：用 contextvars 跟踪「当前 Trace / 当前 Span」。

contextvars 是 asyncio 安全的：每个协程有独立上下文副本，并发任务不会互相污染；set/reset
用 token 恢复，天然支持嵌套（子 Span 退出后自动回到父 Span）。
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# 用 Any 避免与 span / trace 模块的循环 import；真实类型由 Tracer 约束。
_current_trace: ContextVar[Any | None] = ContextVar("agenttrace_current_trace", default=None)
_current_span: ContextVar[Any | None] = ContextVar("agenttrace_current_span", default=None)
