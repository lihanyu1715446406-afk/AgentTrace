"""异步数据库引擎与会话工厂。

引擎惰性建连：首次真正执行 SQL 时才建立连接，因此导入本模块不会触发数据库连接。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import get_settings

_settings = get_settings()

engine = create_async_engine(_settings.database_url, echo=False, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：为每个请求提供一个独立的异步会话。"""
    async with async_session_factory() as session:
        yield session
