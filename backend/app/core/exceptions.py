"""应用自定义异常。"""

from __future__ import annotations


class AgentTraceError(Exception):
    """AgentTrace 业务异常基类。"""


class NotFoundError(AgentTraceError):
    """资源不存在。"""


class ValidationError(AgentTraceError):
    """业务校验失败。"""


class LLMError(AgentTraceError):
    """LLM 调用失败。"""


class ToolExecutionError(AgentTraceError):
    """工具执行失败。"""


class AuthenticationError(AgentTraceError):
    """API Key 无效或项目不存在（SDK 鉴权失败）。"""
