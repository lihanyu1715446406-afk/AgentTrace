"""M1 演示脚本：用 DeepSeek 单 Agent 诊断真实数据。

用法（项目根目录）：
    uv run python scripts/seed_demo_data.py                         # 先写入演示数据
    uv run python scripts/diagnose.py "查询 trace tr-demo-001 的详情"
    uv run python scripts/diagnose.py "这个项目花了多少 token？"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.agents import DiagnoseAgent  # noqa: E402
from backend.app.core.database import async_session_factory  # noqa: E402
from backend.app.core.llm import get_llm  # noqa: E402
from backend.app.tools import ToolRegistry  # noqa: E402


def main() -> None:
    # Windows 控制台默认 GBK，emoji/中文可能无法编码；强制 UTF-8 输出。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    query = sys.argv[1] if len(sys.argv) > 1 else "帮我看看演示项目里有哪些 trace？"
    tools = ToolRegistry(async_session_factory).build_all()
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
    else:
        print("（本次未调用工具）")


if __name__ == "__main__":
    main()
