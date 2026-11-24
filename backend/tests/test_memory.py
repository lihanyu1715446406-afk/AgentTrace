"""M5 Memory 测试：长期记忆（写入/去重/检索/更新/巩固）+ 短期记忆（中断恢复）。

说明：长期记忆用隔离的 ``agenttrace_test`` 库；短期记忆用内存 ``InMemorySaver``
（LangGraph 官方测试/调试实现），真实 PG 持久化在 ``scripts/memory_checkpoint_demo.py``
冒烟中验证。
"""

from __future__ import annotations

import json

from backend.app.memory import MemoryManager, WorkingMemory
from backend.app.memory.checkpoint import build_in_memory_checkpointer
from backend.app.schemas.memory import MemoryType
from backend.app.tools import build_memory_search_tool
from backend.tests._fakes import FakeEmbedding, make_in_memory_store


async def test_record_creates_and_dedupes(session_factory, seeded) -> None:
    manager = MemoryManager(session_factory)
    first = await manager.record(seeded["project_id"], MemoryType.EPISODIC, "支付回调出现上游超时")
    assert first.created is True

    second = await manager.record(seeded["project_id"], MemoryType.EPISODIC, "支付回调出现上游超时")
    assert second.created is False
    assert second.memory_id == first.memory_id

    third = await manager.record(seeded["project_id"], MemoryType.EPISODIC, "登录链路执行正常")
    assert third.created is True
    assert third.memory_id != first.memory_id


async def test_recall_by_keyword_and_type(session_factory, seeded) -> None:
    manager = MemoryManager(session_factory)
    await manager.record(seeded["project_id"], MemoryType.EPISODIC, "支付回调出现上游超时错误")
    await manager.record(seeded["project_id"], MemoryType.SEMANTIC, "上游超时通常由网络抖动导致")

    hits = await manager.recall(seeded["project_id"], "超时")
    assert len(hits.hits) == 2

    only_episodic = await manager.recall(
        seeded["project_id"], "超时", memory_type=MemoryType.EPISODIC
    )
    assert len(only_episodic.hits) == 1
    assert only_episodic.hits[0].memory_type == "EPISODIC"
    assert only_episodic.hits[0].project_id == seeded["project_id"]


async def test_update_memory(session_factory, seeded) -> None:
    manager = MemoryManager(session_factory)
    created = await manager.record(seeded["project_id"], MemoryType.SEMANTIC, "旧结论")
    updated = await manager.update(created.memory_id, "新结论")
    assert updated.content == "新结论"
    assert updated.memory_id == created.memory_id

    hits = await manager.recall(seeded["project_id"], "新结论")
    assert any(h.memory_id == created.memory_id for h in hits.hits)


async def test_consolidate_episodic_to_semantic(session_factory, seeded) -> None:
    async def fake_distill(episodes) -> str:
        assert len(episodes) == 2
        return "上游超时的典型根因是网络抖动与下游过载。"

    manager = MemoryManager(session_factory, distill=fake_distill)
    await manager.record(seeded["project_id"], MemoryType.EPISODIC, "案例A：上游超时因网络抖动")
    await manager.record(seeded["project_id"], MemoryType.EPISODIC, "案例B：上游超时因下游过载")

    result = await manager.consolidate(seeded["project_id"])
    assert result.semantic_memory is not None
    assert result.semantic_memory.memory_type == "SEMANTIC"
    assert "上游超时" in result.semantic_memory.content
    assert len(result.source_memory_ids) == 2


async def test_consolidate_no_episodic_skips(session_factory, seeded) -> None:
    async def fake_distill(episodes) -> str:
        return "不应被调用"

    manager = MemoryManager(session_factory, distill=fake_distill)
    result = await manager.consolidate(seeded["project_id"])
    assert result.semantic_memory is None
    assert result.skipped_reason is not None


async def test_memory_search_tool(session_factory, seeded) -> None:
    manager = MemoryManager(session_factory)
    await manager.record(seeded["project_id"], MemoryType.EPISODIC, "支付回调上游超时")

    tool = build_memory_search_tool(manager)
    output = await tool.ainvoke({"query": "超时", "project_id": seeded["project_id"], "top_k": 5})
    data = json.loads(output)
    assert data["hits"]
    assert "超时" in data["hits"][0]["content"]


async def test_working_memory_interrupt_and_resume() -> None:
    wm = WorkingMemory(build_in_memory_checkpointer())

    snap = await wm.start("支付回调失败", "thread-1")
    assert snap.interrupted is True
    assert snap.draft
    assert snap.final_report is None
    assert snap.approved is None

    done = await wm.resume("thread-1", True)
    assert done.interrupted is False
    assert done.approved is True
    assert done.final_report


async def test_working_memory_resume_reject() -> None:
    wm = WorkingMemory(build_in_memory_checkpointer())
    snap = await wm.start("成本偏高", "thread-2")
    assert snap.interrupted is True

    done = await wm.resume("thread-2", False)
    assert done.interrupted is False
    assert done.approved is False
    assert "未获确认" in (done.final_report or "")


async def test_record_semantic_dedup_for_semantic_type(session_factory, seeded) -> None:
    """语义模式下，SEMANTIC 写入对措辞不同但含义相同的记忆做语义去重。"""
    manager = MemoryManager(
        session_factory,
        embedding=FakeEmbedding(),
        vector_index=await make_in_memory_store(collection="test_memory_semantic"),
        semantic_threshold=0.85,
    )
    first = await manager.record(
        seeded["project_id"], MemoryType.SEMANTIC, "上游超时由网络抖动导致"
    )
    assert first.created is True

    second = await manager.record(
        seeded["project_id"], MemoryType.SEMANTIC, "上游超时由网络抖动所致"
    )
    assert second.created is False
    assert second.memory_id == first.memory_id


async def test_semantic_dedup_only_applies_to_semantic_type(session_factory, seeded) -> None:
    """语义去重只对 SEMANTIC 生效；EPISODIC 仍只做精确内容去重。"""
    manager = MemoryManager(
        session_factory,
        embedding=FakeEmbedding(),
        vector_index=await make_in_memory_store(collection="test_memory_semantic_ep"),
        semantic_threshold=0.85,
    )
    first = await manager.record(
        seeded["project_id"], MemoryType.EPISODIC, "上游超时由网络抖动导致"
    )
    second = await manager.record(
        seeded["project_id"], MemoryType.EPISODIC, "上游超时由网络抖动所致"
    )
    assert first.created is True
    assert second.created is True
    assert second.memory_id != first.memory_id


async def test_recall_semantic(session_factory, seeded) -> None:
    """语义模式下检索走向量相似度，并仍按 project_id / memory_type 过滤。"""
    manager = MemoryManager(
        session_factory,
        embedding=FakeEmbedding(),
        vector_index=await make_in_memory_store(collection="test_memory_recall"),
    )
    await manager.record(seeded["project_id"], MemoryType.SEMANTIC, "上游超时通常由网络抖动导致")
    await manager.record(seeded["project_id"], MemoryType.EPISODIC, "支付回调出现上游超时")

    hits = await manager.recall(seeded["project_id"], "超时 网络", memory_type=MemoryType.SEMANTIC)
    assert hits.hits
    assert all(h.memory_type == "SEMANTIC" for h in hits.hits)
    assert all(h.project_id == seeded["project_id"] for h in hits.hits)
