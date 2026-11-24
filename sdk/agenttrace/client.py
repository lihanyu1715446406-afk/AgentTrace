"""AgentTraceClient：SDK 与后端服务的 HTTP 客户端（异步上报 + 查询）。"""

from __future__ import annotations

import httpx

from .exporters import HTTPExporter
from .trace import Trace


class AgentTraceClient:
    """持有 endpoint / api_key / project_id，统一为上报与查询附加鉴权头。"""

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        project_id: str,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._project_id = project_id
        self._exporter = HTTPExporter(endpoint=endpoint, transport=transport, timeout=timeout)

    @property
    def project_id(self) -> str:
        return self._project_id

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    async def flush(self, trace: Trace) -> dict:
        """异步上报一条完整 Trace，返回后端回执。"""
        return await self._exporter.post(
            path="/ingest/trace",
            payload=trace.to_payload(self._project_id),
            headers=self._headers(),
        )

    async def list_traces(self) -> list[dict]:
        """查询本项目已采集的 Trace 列表。"""
        return await self._exporter.get(
            path="/traces",
            params={"project_id": self._project_id},
            headers=self._headers(),
        )

    async def get_trace(self, trace_id: str) -> dict:
        """查询单条 Trace 的完整结构（spans 树 + token + 成本）。"""
        return await self._exporter.get(
            path=f"/traces/{trace_id}",
            params={"project_id": self._project_id},
            headers=self._headers(),
        )
