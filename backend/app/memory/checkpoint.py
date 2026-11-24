"""Checkpointer 连接配置。

生产用 PostgreSQL（``langgraph-checkpoint-postgres`` 的 ``AsyncPostgresSaver``），
测试/调试用内存版（``InMemorySaver``，重启即丢）。连接串复用全局 PostgreSQL 配置。
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from ..core.config import get_settings


def get_checkpoint_conn_string() -> str:
    """构造 psycopg 连接串，供 ``AsyncPostgresSaver.from_conn_string`` 使用。"""
    settings = get_settings()
    return (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def build_in_memory_checkpointer() -> BaseCheckpointSaver:
    """构建内存 checkpointer（仅用于测试/调试，不持久化）。"""
    return InMemorySaver()
