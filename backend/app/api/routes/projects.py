"""项目接入路由：创建项目、列出项目。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...repositories import ProjectRepository
from ...schemas.ingest import ProjectCreate, ProjectCreateResult, ProjectRead
from ...services.ingest_service import IngestService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectCreateResult, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectCreateResult:
    """创建项目并返回一次性 API Key（此后只存哈希）。"""
    project_id, api_key = await IngestService(db).create_project(body.name)
    return ProjectCreateResult(project_id=project_id, name=body.name, api_key=api_key)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> list[ProjectRead]:
    """列出全部项目（供 Dashboard 选择项目）。"""
    projects = await ProjectRepository(db).list()
    return [ProjectRead(project_id=p.id, name=p.name) for p in projects]
