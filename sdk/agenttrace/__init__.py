"""AgentTrace Python SDK：供外部 Python Agent 采集 Trace / Span / Token 并异步上报。

用法示例：:

    from sdk.agenttrace import AgentTraceClient, Tracer, TraceCallbackHandler

    client = AgentTraceClient(endpoint=..., api_key=..., project_id=...)
    tracer = Tracer(client)

    with tracer.trace("任务名"):
        with tracer.span("llm", span_type="llm"):
            ...
    await tracer.flush(...)
"""

from .client import AgentTraceClient
from .langgraph import TraceCallbackHandler
from .span import Span
from .trace import Trace
from .tracer import Tracer

__all__ = ["AgentTraceClient", "Tracer", "Trace", "Span", "TraceCallbackHandler"]
