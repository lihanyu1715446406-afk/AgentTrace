"""MemoryManager：长期记忆（Episodic/Semantic）的写入、检索、更新、去重、巩固。

支持两种检索/去重模式：

- **关键词模式（默认）**：写入用精确内容去重，检索用 PG ``ILIKE`` 关键词匹配。
- **语义模式**：注入 ``embedding`` + ``vector_index`` 后，检索改为向量相似度，SEMANTIC
  类型的写入增加「语义相似去重」（解决 LLM 巩固措辞不同导致的重复语义记忆）。

语义模式依赖外部能力（SiliconFlow embedding + Qdrant），测试可用假 embedding + 内存 Qdrant
隔离；关键词模式不依赖任何外部服务，保持 M5 行为不变。
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Protocol, cast

from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.exceptions import NotFoundError
from ..models import MemoryRecord
from ..rag.embedding import EmbeddingProvider
from ..repositories.memory_record_repository import MemoryRecordRepository
from ..schemas.memory import (
    ConsolidationDraft,
    ConsolidationResult,
    MemoryRecordRead,
    MemorySearchResult,
    MemoryType,
    MemoryWriteResult,
)

# 巩固提炼函数：把若干条情景记忆（MemoryRecord）提炼成一条语义记忆正文。
type DistillFunc = Callable[[list[MemoryRecord]], Awaitable[str]]


class MemoryVectorIndex(Protocol):
    """记忆向量索引的最小接口（由 ``rag.vector_store.QdrantVectorStore`` 等实现）。

    只声明语义模式用到的三个方法，便于测试用内存 Qdrant 替换生产实现。
    """

    async def ensure_collection(self) -> None: ...

    async def upsert(self, points: list[dict]) -> None: ...

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 4,
        *,
        filters: dict[str, str] | None = None,
    ) -> list[dict]: ...


_CONSOLIDATE_PROMPT = (
    "你是 AgentTrace 平台的记忆巩固器。请阅读下面若干条历史诊断经历（情景记忆），"
    "提炼出一条通用、可复用的语义记忆正文（例如：某类故障的典型根因与排查要点）。"
    "只依据给出的经历，不要编造新的经历。\n\n"
    "历史经历：\n"
)

# 语义去重阈值：向量余弦相似度 >= 该值视为「同一条语义记忆」。
_DEFAULT_SEMANTIC_THRESHOLD = 0.9


def _memory_to_read(memory: MemoryRecord) -> MemoryRecordRead:
    return MemoryRecordRead(
        memory_id=memory.memory_id,
        project_id=str(memory.project_id),
        memory_type=memory.memory_type,
        content=memory.content,
        source_task_id=memory.source_task_id,
        metadata=memory.metadata_,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )


def _coerce_project_id(project_id: str | uuid.UUID) -> uuid.UUID:
    if isinstance(project_id, uuid.UUID):
        return project_id
    try:
        return uuid.UUID(project_id)
    except ValueError as exc:
        raise ValueError(f"非法的 project_id: {project_id}") from exc


def _to_memory_id(point_id: str) -> str:
    """把 Qdrant 返回的 point id 转回 memory_id 的 32 位 hex 形式。

    ``_index`` 用 ``uuid.uuid4().hex`` 作为 point id；Qdrant 会把它归一化成带连字符的
    UUID，检索后需转回 hex 才能与 ``MemoryRecord.memory_id``（32 位 hex）匹配。
    """
    return uuid.UUID(point_id).hex


class MemoryManager:
    """统一管理长期记忆：写入（去重）、检索、更新、巩固。

    - Episodic / Semantic 都落在 ``MemoryRecord`` 表，用 ``memory_type`` 区分。
    - 巩固（consolidate）用 LLM 把多条情景记忆提炼成语义记忆；测试可注入 ``distill`` 隔离 LLM。
    - 传入 ``embedding`` + ``vector_index`` 后启用语义模式：检索走向量、SEMANTIC 写入走语义去重。
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        llm: BaseChatModel | None = None,
        distill: DistillFunc | None = None,
        embedding: EmbeddingProvider | None = None,
        vector_index: MemoryVectorIndex | None = None,
        semantic_threshold: float = _DEFAULT_SEMANTIC_THRESHOLD,
    ) -> None:
        self._session_factory = session_factory
        self._llm = llm
        self._distill = distill
        self._embedding = embedding
        self._vector_index = vector_index
        self._semantic_threshold = semantic_threshold
        self._collection_ensured = False

    @property
    def _semantic_enabled(self) -> bool:
        return self._embedding is not None and self._vector_index is not None

    async def record(
        self,
        project_id: str | uuid.UUID,
        memory_type: MemoryType,
        content: str,
        *,
        source_task_id: str | None = None,
        metadata: dict | None = None,
    ) -> MemoryWriteResult:
        """写入一条长期记忆；同项目同类型下内容相同（或语义相似，仅 SEMANTIC）则去重。

        精确去重对所有类型生效；语义去重仅在「启用语义模式且类型为 SEMANTIC」时生效，
        用于解决 LLM 巩固产生的措辞不同但含义相同的重复语义记忆。
        """
        pid = _coerce_project_id(project_id)
        normalized = content.strip()
        if not normalized:
            raise ValueError("记忆内容不能为空")

        async with self._session_factory() as session:
            repo = MemoryRecordRepository(session)
            dup = await repo.find_duplicate(pid, memory_type.value, normalized)
            if dup is None and memory_type is MemoryType.SEMANTIC:
                dup = await self._find_semantic_duplicate(repo, pid, normalized)
            now = datetime.now(UTC)
            if dup is not None:
                dup.updated_at = now
                if metadata is not None:
                    dup.metadata_ = metadata
                await session.commit()
                await self._index(dup)
                return MemoryWriteResult(
                    memory_id=dup.memory_id,
                    memory_type=memory_type.value,
                    content=dup.content,
                    created=False,
                    updated_at=dup.updated_at,
                )

            memory = await repo.add(
                MemoryRecord(
                    memory_id=uuid.uuid4().hex,
                    project_id=pid,
                    memory_type=memory_type.value,
                    content=normalized,
                    source_task_id=source_task_id,
                    metadata_=metadata,
                )
            )
            memory.updated_at = now
            await session.commit()
            await self._index(memory)
            return MemoryWriteResult(
                memory_id=memory.memory_id,
                memory_type=memory_type.value,
                content=memory.content,
                created=True,
                updated_at=memory.updated_at,
            )

    async def recall(
        self,
        project_id: str | uuid.UUID,
        query: str,
        *,
        memory_type: MemoryType | None = None,
        limit: int = 5,
    ) -> MemorySearchResult:
        """检索历史记忆：语义模式走向量相似度，否则走关键词（ILIKE）。"""
        pid = _coerce_project_id(project_id)
        mtype_value = memory_type.value if memory_type else None

        if self._semantic_enabled:
            await self._ensure_collection()
            assert self._embedding is not None and self._vector_index is not None
            query_vector = await self._embedding.aembed_query(query)
            filters = {"project_id": str(pid)}
            if mtype_value:
                filters["memory_type"] = mtype_value
            results = await self._vector_index.search(query_vector, top_k=limit, filters=filters)
            async with self._session_factory() as session:
                repo = MemoryRecordRepository(session)
                hits = [
                    _memory_to_read(memory)
                    for result in results
                    if (memory := await repo.get_by_memory_id(_to_memory_id(result["id"])))
                    is not None
                ]
            return MemorySearchResult(query=query, memory_type=mtype_value, hits=hits)

        async with self._session_factory() as session:
            repo = MemoryRecordRepository(session)
            memories = await repo.search(pid, query, mtype_value, limit=limit)
        return MemorySearchResult(
            query=query,
            memory_type=mtype_value,
            hits=[_memory_to_read(m) for m in memories],
        )

    async def update(self, memory_id: str, content: str) -> MemoryWriteResult:
        """显式更新一条记忆的内容（并刷新 updated_at、重建向量索引）。"""
        normalized = content.strip()
        if not normalized:
            raise ValueError("记忆内容不能为空")

        async with self._session_factory() as session:
            repo = MemoryRecordRepository(session)
            memory = await repo.get_by_memory_id(memory_id)
            if memory is None:
                raise NotFoundError(f"未找到记忆 memory_id={memory_id}")
            memory.content = normalized
            memory.updated_at = datetime.now(UTC)
            await session.commit()
            await self._index(memory)
            return MemoryWriteResult(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                content=memory.content,
                created=False,
                updated_at=memory.updated_at,
            )

    async def consolidate(
        self,
        project_id: str | uuid.UUID,
        *,
        limit: int = 10,
    ) -> ConsolidationResult:
        """记忆巩固：取最近若干条情景记忆，提炼为一条语义记忆并写入（带去重）。"""
        pid = _coerce_project_id(project_id)
        async with self._session_factory() as session:
            repo = MemoryRecordRepository(session)
            episodes = await repo.list_by_project(pid, MemoryType.EPISODIC.value, limit=limit)

        if not episodes:
            return ConsolidationResult(source_memory_ids=[], skipped_reason="无情景记忆可巩固")

        content = (await self._distill_episodes(episodes)).strip()
        result = await self.record(
            pid, MemoryType.SEMANTIC, content, source_task_id=episodes[0].source_task_id
        )
        return ConsolidationResult(
            source_memory_ids=[e.memory_id for e in episodes],
            semantic_memory=result,
        )

    async def _distill_episodes(self, episodes: list[MemoryRecord]) -> str:
        if self._distill is not None:
            return await self._distill(episodes)
        if self._llm is None:
            raise ValueError("记忆巩固需要注入 LLM 或 distill 函数")
        runnable = self._llm.with_structured_output(ConsolidationDraft, method="function_calling")
        body = "\n\n".join(f"- {e.content}" for e in episodes)
        draft = cast(ConsolidationDraft, await runnable.ainvoke(_CONSOLIDATE_PROMPT + body))
        return draft.content

    async def _ensure_collection(self) -> None:
        """惰性确保向量集合存在（每个 Manager 实例只做一次）。"""
        if self._vector_index is not None and not self._collection_ensured:
            await self._vector_index.ensure_collection()
            self._collection_ensured = True

    async def _index(self, memory: MemoryRecord) -> None:
        """把一条记忆的向量写入索引（语义模式启用时）。"""
        if not self._semantic_enabled or self._embedding is None or self._vector_index is None:
            return
        await self._ensure_collection()
        vector = (await self._embedding.aembed_documents([memory.content]))[0]
        await self._vector_index.upsert(
            [
                {
                    "id": memory.memory_id,
                    "vector": vector,
                    "payload": {
                        "project_id": str(memory.project_id),
                        "memory_type": memory.memory_type,
                    },
                }
            ]
        )

    async def _find_semantic_duplicate(
        self,
        repo: MemoryRecordRepository,
        pid: uuid.UUID,
        content: str,
    ) -> MemoryRecord | None:
        """语义相似去重：找同项目同类型下语义最相近的一条，相似度达标则返回它。"""
        if not self._semantic_enabled or self._embedding is None or self._vector_index is None:
            return None
        await self._ensure_collection()
        query_vector = await self._embedding.aembed_query(content)
        results = await self._vector_index.search(
            query_vector,
            top_k=1,
            filters={
                "project_id": str(pid),
                "memory_type": MemoryType.SEMANTIC.value,
            },
        )
        if not results or results[0]["score"] < self._semantic_threshold:
            return None
        return await repo.get_by_memory_id(_to_memory_id(results[0]["id"]))
