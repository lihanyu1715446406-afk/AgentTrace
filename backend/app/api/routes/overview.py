"""Overview 仪表盘路由：全局指标聚合。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...repositories import OverviewRepository
from ...schemas import Overview

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=Overview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """返回全局指标（trace/span/project 计数、token 成本、最近 trace）。"""
    return await OverviewRepository(db).summary()
