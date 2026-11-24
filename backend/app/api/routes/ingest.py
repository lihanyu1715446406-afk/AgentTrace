"""SDK 数据上报路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.exceptions import AuthenticationError
from ...schemas.ingest import IngestResult, TraceIngest
from ...services.ingest_service import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/trace", response_model=IngestResult, status_code=status.HTTP_201_CREATED)
async def ingest_trace(
    payload: TraceIngest,
    x_api_key: str = Header(alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """接收 SDK 上报的一条完整 Trace（含 spans 与 token 用量）。"""
    try:
        return await IngestService(db).ingest(api_key=x_api_key, payload=payload)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
