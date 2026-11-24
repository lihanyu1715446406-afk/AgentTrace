"""采集数据写入仓库（与只读查询仓库分离）。"""

from __future__ import annotations

import uuid

from ..models import Project, Span, TokenUsage, Trace
from .base import BaseRepository


class IngestRepository(BaseRepository):
    """SDK 上报数据的写入仓库。"""

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def save_trace(
        self,
        trace: Trace,
        spans: list[Span],
        usages: list[TokenUsage],
    ) -> None:
        """把一条 Trace 及其 spans / token 用量一起写入（flush 不提交，由服务层决定）。

        TokenUsage 只有外键、没有 relationship（Span 有 ``trace`` 关系，SQLAlchemy 会先
        插 traces 再插 spans），因此 unit of work 无法据此排定它的插入顺序，必须先 flush
        trace + spans，再写入 token 用量，避免触发 ``token_usages_trace_id_fkey`` 外键违规。
        """
        self.session.add(trace)
        if spans:
            self.session.add_all(spans)
        await self.session.flush()
        if usages:
            self.session.add_all(usages)
            await self.session.flush()
