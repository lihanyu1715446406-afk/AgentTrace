"""HTTP 上报器：把采集 payload 异步发送到后端。"""

from __future__ import annotations

from typing import Any

import httpx


class HTTPExporter:
    """把采集数据通过 HTTP 上报到 AgentTrace 后端（可注入 transport 便于测试）。"""

    def __init__(
        self,
        *,
        endpoint: str,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._transport = transport
        self._timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._endpoint, transport=self._transport, timeout=self._timeout
        )

    async def post(self, *, path: str, payload: dict, headers: dict[str, str]) -> Any:
        async with self._client() as client:
            resp = await client.post(path, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get(self, *, path: str, params: dict[str, str], headers: dict[str, str]) -> Any:
        async with self._client() as client:
            resp = await client.get(path, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
