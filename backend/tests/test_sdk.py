"""SDK 层测试：Trace/Span 管理、父子关系、token 记录、装饰器与上报 payload。"""

from __future__ import annotations

import json

import httpx

from sdk.agenttrace import AgentTraceClient, Span, Trace, Tracer


def test_trace_and_span_parent_child_relationship():
    tracer = Tracer()
    with tracer.trace("诊断登录") as trace:
        with tracer.span("llm_call", span_type="llm"):
            with tracer.span("tool_call", span_type="tool") as child:
                assert child.span_id

    assert trace.status == "success"
    assert trace.duration_ms is not None
    assert len(trace.spans) == 2
    root_span, child_span = trace.spans
    assert root_span.parent_span_id is None
    assert child_span.parent_span_id == root_span.span_id


def test_span_records_token_usage():
    tracer = Tracer()
    with tracer.trace("任务") as trace:
        span = tracer.start_span("llm", span_type="llm")
        span.record_token_usage(
            model_name="deepseek-chat",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        tracer.end_span(span)

    usages = trace.token_usages()
    assert len(usages) == 1
    assert usages[0]["model_name"] == "deepseek-chat"
    assert usages[0]["total_tokens"] == 15
    assert usages[0]["span_id"] == span.span_id


def test_tracer_sync_decorator_runs_function():
    tracer = Tracer()
    seen: list[str] = []

    @tracer.trace
    def work():
        seen.append("ran")
        return 42

    assert work() == 42
    assert seen == ["ran"]


async def test_tracer_async_decorator_flushes_trace():
    class _FakeClient:
        project_id = "proj-1"

        def __init__(self):
            self.flushed: list[Trace] = []

        async def flush(self, trace: Trace) -> dict:
            self.flushed.append(trace)
            return {
                "trace_id": trace.trace_id,
                "span_count": len(trace.spans),
                "token_usage_count": 0,
            }

    fake = _FakeClient()
    tracer = Tracer(client=fake)

    @tracer.trace
    async def work():
        with tracer.span("step", span_type="chain"):
            pass
        return "done"

    result = await work()
    assert result == "done"
    assert len(fake.flushed) == 1
    trace = fake.flushed[0]
    assert trace.name == "work"
    assert len(trace.spans) == 1


async def test_client_builds_ingest_payload_and_headers():
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["api_key"] = request.headers.get("x-api-key")
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"trace_id": "t1", "span_count": 1, "token_usage_count": 1})

    client = AgentTraceClient(
        endpoint="http://localhost:8000",
        api_key="secret",
        project_id="p1",
        transport=httpx.MockTransport(handler),
    )

    trace = Trace(trace_id="t1", name="任务", project_id="p1")
    span = Span(span_id="s1", name="llm", span_type="llm")
    span.record_token_usage(model_name="m", prompt_tokens=1, completion_tokens=2, total_tokens=3)
    span.end()
    trace.spans.append(span)
    trace.end()

    result = await client.flush(trace)

    assert captured["path"] == "/ingest/trace"
    assert captured["api_key"] == "secret"
    body = captured["body"]
    assert body["trace_id"] == "t1"
    assert body["project_id"] == "p1"
    assert body["spans"][0]["span_id"] == "s1"
    assert body["token_usages"][0]["model_name"] == "m"
    assert result == {"trace_id": "t1", "span_count": 1, "token_usage_count": 1}
