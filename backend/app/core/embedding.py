"""Embedding 接入：SiliconFlow（OpenAI 兼容）工厂。"""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from .config import get_settings
from .exceptions import LLMError
from .http import build_http_clients


def get_embedding() -> OpenAIEmbeddings:
    """构建 SiliconFlow 的 OpenAIEmbeddings 客户端（bge-m3，1024 维）。

    - DeepSeek 无 embeddings 接口，RAG 向量化走 SiliconFlow（OpenAI 兼容 ``/v1/embeddings``）。
    - 密钥只从配置（环境变量 / .env）读取，不在此硬编码。
    """
    settings = get_settings()
    if not settings.siliconflow_api_key:
        raise LLMError(
            "未检测到 SILICONFLOW_API_KEY。请通过环境变量或 .env 注入密钥（禁止硬编码）。"
        )
    http_client, http_async_client = build_http_clients()
    return OpenAIEmbeddings(
        model=settings.siliconflow_embedding_model,
        api_key=SecretStr(settings.siliconflow_api_key),
        base_url=settings.siliconflow_base_url,
        http_client=http_client,
        http_async_client=http_async_client,
    )
