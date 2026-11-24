"""M5 演示脚本：中断恢复（PostgreSQL Checkpointer）。

用法（项目根目录，需先启动 PostgreSQL 并安装 langgraph-checkpoint-postgres）：
    uv add langgraph-checkpoint-postgres
    uv run python scripts/memory_checkpoint_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.memory import WorkingMemory  # noqa: E402
from backend.app.memory.checkpoint import get_checkpoint_conn_string  # noqa: E402


async def _run() -> None:
    # 延迟导入：只有本脚本需要 PG checkpointer，核心测试用内存版即可。
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    async with AsyncPostgresSaver.from_conn_string(get_checkpoint_conn_string()) as saver:
        await saver.setup()

        wm = WorkingMemory(saver)
        thread_id = "demo-thread-001"

        # 第一次：运行到人工确认点（interrupt），checkpoint 已落盘到 PostgreSQL。
        snap = await wm.start("支付回调失败，请诊断", thread_id)
        print(f"[中断] interrupted={snap.interrupted}")
        print(f"       draft={snap.draft}")
        print("       （此处模拟进程重启：换新进程也能用同一 thread_id 续跑）")

        # 第二次：用同一 thread_id 从 checkpoint 恢复，传入人工决定，完成定稿。
        done = await wm.resume(thread_id, True)
        print(f"[恢复] interrupted={done.interrupted}，approved={done.approved}")
        print(f"       final_report={done.final_report}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
