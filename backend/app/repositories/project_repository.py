"""项目查询仓库（只读）。"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from ..models import Project
from .base import BaseRepository


class ProjectRepository(BaseRepository):
    """查询项目列表的只读仓库。"""

    async def list(self, limit: int = 100, offset: int = 0) -> list[Project]:
        result = await self.session.execute(
            select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Project | None:
        """按项目名查询；同名取最早创建的一条。"""
        result = await self.session.execute(select(Project).where(Project.name == name).limit(1))
        return result.scalars().first()

    async def resolve(self, identifier: str) -> uuid.UUID | None:
        """把项目标识符（UUID 字符串或项目名）解析为 UUID；找不到返回 None。

        供工具层/MCP 层统一做「名称 vs UUID」解析：用户既可以说项目名，也可以给 UUID。
        """
        try:
            return uuid.UUID(identifier)
        except ValueError:
            project = await self.get_by_name(identifier)
            return project.id if project else None
