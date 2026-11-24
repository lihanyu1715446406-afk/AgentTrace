"""MCP Client 冒烟：通过 MCP 协议调用 AgentTrace 只读诊断工具（M8 验收）。

用法（项目根目录，先写入演示数据）：
    uv run python scripts/seed_demo_data.py
    uv run python scripts/mcp_client_demo.py

通过 stdio 拉起 ``mcp_server.server``，用官方 MCP 客户端连接并调用工具，
证明「MCP Client 可调用工具」这一 M8 验收目标。
"""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _text(content) -> str:
    """把 CallToolResult.content 里的文本块拼成字符串。"""
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


async def _run() -> None:
    params = StdioServerParameters(command="uv", args=["run", "python", "-m", "mcp_server.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("可用 MCP 工具：")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            result = await session.call_tool("cost_analysis", {"trace_id": "tr-demo-001"})
            print("\ncost_analysis(tr-demo-001) =>")
            print(_text(result.content))

            result = await session.call_tool("trace_query", {"trace_id": "tr-demo-002"})
            print("\ntrace_query(tr-demo-002) =>")
            print(_text(result.content))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
