"""LLM 接入：DeepSeek（OpenAI 兼容）工厂。"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from .config import get_settings
from .exceptions import LLMError
from .http import build_http_clients


def get_llm() -> ChatOpenAI:
    """构建 DeepSeek 的 ChatOpenAI 客户端。

    - 使用 ``deepseek-chat``（支持 function calling）；``deepseek-reasoner`` 不支持工具调用。
    - 密钥只从配置（环境变量 / .env）读取，不在此硬编码。
    - 证书处理见 ``core.http.build_http_clients``（Windows 用系统证书库覆盖 certifi）。
    """
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise LLMError("未检测到 DEEPSEEK_API_KEY。请通过环境变量或 .env 注入密钥（禁止硬编码）。")
    http_client, http_async_client = build_http_clients()
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        temperature=0,
        http_client=http_client,
        http_async_client=http_async_client,
    )
