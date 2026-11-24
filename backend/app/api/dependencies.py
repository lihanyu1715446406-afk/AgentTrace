"""API 依赖注入：SDK 鉴权、诊断接口的 LLM / 工具注入等。"""

from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import async_session_factory, get_db
from ..core.exceptions import AuthenticationError
from ..core.llm import get_llm
from ..services.ingest_service import IngestService
from ..tools.base import ToolRegistry


async def authenticate_project(
    project_id: uuid.UUID,
    x_api_key: str = Header(alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """校验 ``X-API-Key`` 与项目匹配，通过则返回 project_id，否则 401。"""
    try:
        await IngestService(db).authenticate(project_id=project_id, api_key=x_api_key)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return project_id


def get_llm_dependency() -> BaseChatModel:
    """诊断接口的 LLM 依赖（测试用 ``dependency_overrides`` 替换为假模型）。"""
    return get_llm()


def get_tools_dependency() -> list[BaseTool]:
    """诊断接口的工具依赖（测试可替换为指向隔离库的工具集合）。"""
    return ToolRegistry(async_session_factory).build_all()
