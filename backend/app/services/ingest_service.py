"""数据采集（ingest）业务服务：SDK 鉴权 + 把上报数据写入 PostgreSQL。

SDK 通过 HTTP 上报（ADR-0006），本服务校验 ``X-API-Key`` 与 ``Project.api_key_hash``
匹配后，把 Trace / Span / TokenUsage 一次性落库。API Key 只存哈希（数据库设计 2.1），
比对用 ``secrets.compare_digest`` 常数时间比较，避免时序侧信道。
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import AuthenticationError
from ..models import Project, Span, TokenUsage, Trace
from ..repositories.ingest_repository import IngestRepository
from ..schemas.ingest import IngestResult, SpanIngest, TokenUsageIngest, TraceIngest

_API_KEY_PREFIX = "agt_"


def hash_api_key(raw: str) -> str:
    """把明文 API Key 哈希为存储值（sha256 十六进制）。"""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """生成一个新的 SDK API Key（带可辨识前缀，仅创建时返回一次明文）。"""
    return _API_KEY_PREFIX + secrets.token_urlsafe(32)


def verify_api_key(raw: str, expected_hash: str) -> bool:
    """常数时间比较 API Key 与存储哈希。"""
    return secrets.compare_digest(hash_api_key(raw), expected_hash)


class IngestService:
    """采集业务：鉴权 + 数据落库。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = IngestRepository(session)

    async def create_project(self, name: str) -> tuple[uuid.UUID, str]:
        """创建项目并生成 API Key；返回 (project_id, 明文 api_key)。"""
        raw = generate_api_key()
        project = Project(name=name, api_key_hash=hash_api_key(raw))
        self._session.add(project)
        await self._session.commit()
        return project.id, raw

    async def authenticate(self, *, project_id: uuid.UUID, api_key: str) -> Project:
        """校验项目存在且 API Key 匹配，返回项目。"""
        project = await self._repo.get_project(project_id)
        if project is None or not verify_api_key(api_key, project.api_key_hash):
            raise AuthenticationError("API Key 无效或项目不存在")
        return project

    async def ingest(self, *, api_key: str, payload: TraceIngest) -> IngestResult:
        """把一条完整 Trace 上报写入数据库。"""
        await self.authenticate(project_id=payload.project_id, api_key=api_key)

        trace = Trace(
            trace_id=payload.trace_id,
            project_id=payload.project_id,
            name=payload.name,
            status=payload.status,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            duration_ms=payload.duration_ms,
            metadata_=payload.metadata,
        )
        spans = [self._to_span(payload.trace_id, s) for s in payload.spans]
        usages = [self._to_usage(payload.trace_id, u) for u in payload.token_usages]

        await self._repo.save_trace(trace, spans, usages)
        await self._session.commit()

        return IngestResult(
            trace_id=payload.trace_id,
            span_count=len(spans),
            token_usage_count=len(usages),
        )

    @staticmethod
    def _to_span(trace_id: str, s: SpanIngest) -> Span:
        return Span(
            span_id=s.span_id,
            trace_id=trace_id,
            parent_span_id=s.parent_span_id,
            name=s.name,
            span_type=s.span_type,
            status=s.status,
            started_at=s.started_at,
            ended_at=s.ended_at,
            duration_ms=s.duration_ms,
            input=s.input,
            output=s.output,
            error=s.error,
            metadata_=s.metadata,
        )

    @staticmethod
    def _to_usage(trace_id: str, u: TokenUsageIngest) -> TokenUsage:
        return TokenUsage(
            trace_id=trace_id,
            span_id=u.span_id,
            model_name=u.model_name,
            prompt_tokens=u.prompt_tokens,
            completion_tokens=u.completion_tokens,
            total_tokens=u.total_tokens,
            estimated_cost=(
                Decimal(str(u.estimated_cost)) if u.estimated_cost is not None else None
            ),
            currency=u.currency,
        )
