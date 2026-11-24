"""LangGraph / LangChain 集成：TraceCallbackHandler 采集 LLM 与工具调用。"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .tracer import Tracer


class TraceCallbackHandler(BaseCallbackHandler):
    """把 LangChain 回调事件映射为 Span，供外部 LangGraph Agent 自动采集。

    配合外层 ``tracer.trace()`` 使用（``config={"callbacks": [handler]}`` 挂到
    ``ainvoke``），``on_llm_start/end`` 采集 LLM 调用与 token，``on_tool_start/end``
    采集工具调用；span 自动挂到当前 trace 下。
    """

    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer
        # run_id -> (span, model_name)；model_name 仅在 llm span 上非空。
        self._spans: dict[Any, tuple[Any, str | None]] = {}

    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        run_id = kwargs.get("run_id")
        if run_id is None:
            return
        model_name = self._extract_model_name(serialized)
        span = self._tracer.start_span(
            model_name or "llm",
            span_type="llm",
            input={"prompts": list(prompts)},
        )
        self._spans[run_id] = (span, model_name)

    def on_llm_end(self, response, **kwargs) -> None:
        entry = self._spans.pop(kwargs.get("run_id"), None)
        if entry is None:
            return
        span, model_name = entry
        usage = self._extract_token_usage(response)
        if usage is not None and model_name:
            span.record_token_usage(
                model_name=model_name,
                prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                completion_tokens=usage.get("completion_tokens", 0) or 0,
                total_tokens=usage.get("total_tokens", 0) or 0,
            )
        self._tracer.end_span(span, output={"generations": self._extract_texts(response)})

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        run_id = kwargs.get("run_id")
        if run_id is None:
            return
        name = serialized.get("name", "tool") if isinstance(serialized, dict) else "tool"
        span = self._tracer.start_span(name, span_type="tool", input={"input": input_str})
        self._spans[run_id] = (span, None)

    def on_tool_end(self, output, **kwargs) -> None:
        entry = self._spans.pop(kwargs.get("run_id"), None)
        if entry is None:
            return
        span, _ = entry
        self._tracer.end_span(span, output={"output": str(output)})

    def on_llm_error(self, error, **kwargs) -> None:
        self._finish_error(kwargs.get("run_id"), error)

    def on_tool_error(self, error, **kwargs) -> None:
        self._finish_error(kwargs.get("run_id"), error)

    def _finish_error(self, run_id, error) -> None:
        entry = self._spans.pop(run_id, None)
        if entry is None:
            return
        span, _ = entry
        self._tracer.end_span(span, status="error", error={"message": str(error)})

    @staticmethod
    def _extract_model_name(serialized) -> str | None:
        if not isinstance(serialized, dict):
            return None
        kwargs = serialized.get("kwargs") or {}
        model = kwargs.get("model")
        if model:
            return model
        ids = serialized.get("id") or []
        return ids[-1] if ids else None

    @staticmethod
    def _extract_token_usage(response) -> dict | None:
        llm_output = getattr(response, "llm_output", None) or {}
        if isinstance(llm_output, dict):
            usage = llm_output.get("token_usage") or llm_output.get("usage")
            if isinstance(usage, dict):
                return usage
        for gen_list in getattr(response, "generations", None) or []:
            for gen in gen_list:
                info = getattr(gen, "generation_info", None) or {}
                if isinstance(info, dict) and "token_usage" in info:
                    return info["token_usage"]
        return None

    @staticmethod
    def _extract_texts(response) -> list[str]:
        texts: list[str] = []
        for gen_list in getattr(response, "generations", None) or []:
            for gen in gen_list:
                text = getattr(gen, "text", None)
                if text:
                    texts.append(str(text))
        return texts
