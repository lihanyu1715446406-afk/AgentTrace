"""M4 演示脚本：带知识检索能力的 Agent 回答知识型问题（保留来源）。

用法（项目根目录，需先入库知识文档）：
    uv run python scripts/ingest_knowledge.py
    uv run python scripts/diagnose_rag.py "如何排查上游超时错误？"
    uv run python scripts/diagnose_rag.py "Token 成本太高怎么优化？"
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import DiagnoseAgent  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.embedding import get_embedding  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.rag import KnowledgeRetriever, QdrantVectorStore  # noqa: E402
from backend.app.tools import ToolRegistry, build_knowledge_search_tool  # noqa: E402


def _print_sources(output: str) -> None:
    """从 knowledge_search 工具输出里解析并打印命中的来源。"""
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return
    for hit in data.get("hits", []):
        title = hit.get("title", "?")
        source = hit.get("source", "?")
        print(f"      ↳ 来源：{title}（{source}）")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    query = sys.argv[1] if len(sys.argv) > 1 else "如何排查上游超时错误？"

    retriever = KnowledgeRetriever(get_embedding(), QdrantVectorStore.from_settings())
    knowledge_tool = build_knowledge_search_tool(retriever)
    tools = ToolRegistry(async_session_factory, knowledge_tool=knowledge_tool).build_all()
    agent = DiagnoseAgent(get_llm(), tools)

    print(f"问题：{query}")
    print("-" * 60)
    result = asyncio.run(agent.arun(query))
    print(f"回答：{result.answer}")
    if result.tool_calls:
        print("-" * 60)
        print("工具调用记录：")
        for call in result.tool_calls:
            print(f"  * {call.tool_name}({call.args})")
            if call.tool_name == "knowledge_search":
                _print_sources(call.output)
    else:
        print("（本次未调用工具）")


if __name__ == "__main__":
    main()
