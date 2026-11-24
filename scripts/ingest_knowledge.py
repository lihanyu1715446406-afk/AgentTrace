"""M4 演示脚本：把演示知识文档写入 Qdrant + PostgreSQL。

用法（项目根目录，需先启动 Qdrant 并设置 SILICONFLOW_API_KEY）：
    docker compose up -d qdrant
    uv run python scripts/ingest_knowledge.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.embedding import get_embedding  # noqa: E402
from backend.app.rag import KnowledgeIngestor, QdrantVectorStore  # noqa: E402

_DEMO_DOCS: list[dict[str, Any]] = [
    {
        "document_id": "kb-timeout",
        "title": "上游超时故障排查",
        "source": "ops-manual",
        "document_type": "md",
        "content": (
            "# 上游超时故障排查\n\n"
            "当 Agent 诊断报告中出现「上游超时」或 span 状态为 error 时，通常由以下原因导致：\n\n"
            "- 下游服务响应缓慢，超过了调用方设置的超时阈值；\n"
            "- 网络抖动或链路不稳定，导致请求重传；\n"
            "- 下游服务瞬时负载过高，排队时间过长。\n\n"
            "排查建议：先查看失败 span 的 error 字段确认具体错误信息，再结合 span 的耗时 "
            "判断是慢调用还是网络问题。若耗时接近超时阈值，优先怀疑下游响应慢；若耗时不长却 "
            "超时，则优先怀疑网络抖动。定位到具体下游后，可检查其监控指标与日志。\n\n"
            "常见处置：对慢调用可调大超时阈值或为下游扩容；对网络抖动可启用重试与熔断策略。\n"
        ),
    },
    {
        "document_id": "kb-cost",
        "title": "Token 成本优化",
        "source": "cost-guide",
        "document_type": "md",
        "content": (
            "# Token 成本优化\n\n"
            "成本分析关注 total_tokens 与 estimated_cost 两个指标。成本偏高时可按以下思路优化：\n\n"
            "- 精简系统提示词与工具描述，减少每次调用的 prompt token；\n"
            "- 控制传给模型的上下文长度，避免把无关历史一并塞入；\n"
            "- 对简单任务使用更便宜的模型，复杂任务再用大模型；\n"
            "- 合理设置工具返回的字段，避免返回冗余数据被再次送入模型。\n\n"
            "注意：estimated_cost 依赖模型价格配置表，价格未知时会标注为估算值。核对成本时 "
            "应优先以计费源为准，而不是仅依赖诊断数据里的估算值。\n"
        ),
    },
]


async def _run() -> None:
    embeddings = get_embedding()
    vector_store = QdrantVectorStore.from_settings()
    ingestor = KnowledgeIngestor(async_session_factory, embeddings, vector_store)

    for doc in _DEMO_DOCS:
        result = await ingestor.ingest_document(**doc)
        print(
            f"已入库：{result.document_id}（{result.title}）"
            f" -> {result.chunks} chunk / {result.points} 向量"
        )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
