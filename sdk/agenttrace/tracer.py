"""Tracer：SDK 顶层 API，管理 Trace / Span 生命周期、父子关系与异步上报。"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, Literal

from .client import AgentTraceClient
from .context import _current_span, _current_trace
from .span import Span
from .trace import Trace


class _TraceContext:
    """``with tracer.trace(...)`` / ``async with tracer.trace(...)`` 的上下文管理器。

    同时实现了 ``__call__``，使 ``@tracer.trace("名字")`` 这种带参装饰器也能工作。
    """

    def __init__(
        self,
        tracer: Tracer,
        *,
        name: str,
        trace_id: str | None = None,
        metadata: dict | None = None,
        flush: bool | None = None,
    ) -> None:
        self._tracer = tracer
        self._name = name
        self._trace_id = trace_id
        self._metadata = metadata
        self._flush = flush
        self.trace: Trace | None = None

    def __call__(self, fn: Callable) -> Callable:
        return self._tracer._decorate(
            fn,
            name=self._name,
            trace_id=self._trace_id,
            metadata=self._metadata,
            flush=self._flush,
        )

    def __enter__(self) -> Trace:
        self.trace = self._tracer.start_trace(
            self._name, trace_id=self._trace_id, metadata=self._metadata
        )
        return self.trace

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        status = "success" if exc_type is None else "error"
        self._tracer.end_trace(self.trace, status=status)
        return False

    async def __aenter__(self) -> Trace:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self.__exit__(exc_type, exc, tb)
        if self._flush:
            await self._tracer.flush(self.trace)
        return False


class _SpanContext:
    """``with tracer.span(...)`` 的上下文管理器，自动结束 Span 并恢复父 Span。"""

    def __init__(
        self,
        tracer: Tracer,
        *,
        name: str,
        span_type: str,
        input: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        self._tracer = tracer
        self._name = name
        self._span_type = span_type
        self._input = input
        self._metadata = metadata
        self.span: Span | None = None

    def __enter__(self) -> Span:
        self.span = self._tracer.start_span(
            self._name,
            span_type=self._span_type,
            input=self._input,
            metadata=self._metadata,
        )
        return self.span

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        status = "success" if exc_type is None else "error"
        error = None
        if exc_type is not None:
            error = {"type": exc_type.__name__, "message": str(exc)}
        self._tracer.end_span(self.span, status=status, error=error)
        return False

    async def __aenter__(self) -> Span:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return self.__exit__(exc_type, exc, tb)


class Tracer:
    """采集入口：创建/结束 Trace 与 Span，维护父子关系，支持异步上报。

    - ``tracer.trace("名字")``：上下文管理器（同步 / 异步）。
    - ``@tracer.trace``：装饰器（函数名作为 trace 名；异步函数自动 flush）。
    - ``tracer.span("名字", span_type=...)``：嵌套 span 上下文管理器。
    """

    def __init__(self, client: AgentTraceClient | None = None) -> None:
        self._client = client

    def start_trace(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        metadata: dict | None = None,
    ) -> Trace:
        trace = Trace(
            trace_id=trace_id,
            name=name,
            project_id=self._client.project_id if self._client else None,
            metadata=metadata,
        )
        trace._context_token = _current_trace.set(trace)
        _current_span.set(None)
        return trace

    def end_trace(self, trace: Trace | None, *, status: str = "success") -> None:
        if trace is None:
            return
        trace.end(status=status)
        token = getattr(trace, "_context_token", None)
        if token is not None:
            _current_trace.reset(token)

    def start_span(
        self,
        name: str,
        *,
        span_type: str = "span",
        span_id: str | None = None,
        parent_span_id: str | None = None,
        input: dict | None = None,
        metadata: dict | None = None,
    ) -> Span:
        trace = _current_trace.get()
        if trace is None:
            raise RuntimeError("当前没有活动 Trace，请先调用 tracer.trace() 或 start_trace()")
        parent = _current_span.get()
        effective_parent = (
            parent_span_id if parent_span_id is not None else (parent.span_id if parent else None)
        )
        span = Span(
            span_id=span_id,
            parent_span_id=effective_parent,
            name=name,
            span_type=span_type,
            input=input,
            metadata=metadata,
        )
        trace.spans.append(span)
        span._context_token = _current_span.set(span)
        return span

    def end_span(
        self,
        span: Span | None,
        *,
        status: str = "success",
        output: dict | None = None,
        error: dict | None = None,
    ) -> None:
        if span is None:
            return
        span.end(status=status, output=output, error=error)
        token = getattr(span, "_context_token", None)
        if token is not None:
            _current_span.reset(token)

    async def flush(self, trace: Trace | None) -> dict | None:
        """异步上报一条 Trace（无 client 时为空操作）。"""
        if self._client is None or trace is None:
            return None
        return await self._client.flush(trace)

    def trace(self, name: str | Callable | None = None, **kwargs: Any) -> Any:
        """作为上下文管理器（``name`` 为 str）或装饰器（``name`` 为 callable）。"""
        if callable(name) and not isinstance(name, str):
            return self._decorate(name, **kwargs)
        return _TraceContext(self, name=name or "trace", **kwargs)

    def span(self, name: str, *, span_type: str = "span", **kwargs: Any) -> _SpanContext:
        return _SpanContext(self, name=name, span_type=span_type, **kwargs)

    def _decorate(
        self,
        fn: Callable,
        *,
        name: str | None = None,
        trace_id: str | None = None,
        metadata: dict | None = None,
        flush: bool | None = None,
    ) -> Callable:
        trace_name = name or fn.__name__
        if inspect.iscoroutinefunction(fn):
            # 异步装饰器默认自动 flush（显式传 flush=False 可关闭）。
            auto_flush = flush if flush is not None else True

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with _TraceContext(
                    self,
                    name=trace_name,
                    trace_id=trace_id,
                    metadata=metadata,
                    flush=auto_flush,
                ):
                    return await fn(*args, **kwargs)

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with _TraceContext(
                self, name=trace_name, trace_id=trace_id, metadata=metadata, flush=False
            ):
                return fn(*args, **kwargs)

        return sync_wrapper
