"""Embedding 抽象：把「文本向量化」与具体 Provider 解耦。"""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """文本向量化能力的最小接口（结构化鸭子类型）。

    具体实现（SiliconFlow 的 ``OpenAIEmbeddings``）由 ``core.embedding.get_embedding``
    提供；测试中可用确定性的假实现替换，避免依赖外部 HTTP 服务。
    """

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """把一批文档片段向量化。"""
        ...

    async def aembed_query(self, text: str) -> list[float]:
        """把一条查询向量化。"""
        ...
