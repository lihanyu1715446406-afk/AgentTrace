"""系统健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """存活探针：返回服务状态。"""
    return {"status": "ok"}
