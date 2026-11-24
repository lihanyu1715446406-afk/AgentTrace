"""M4 RAG 测试：切分、入库、检索、Metadata Filtering、检索工具。

说明：测试用确定性的字符哈希向量（``FakeEmbedding``）+ Qdrant 内存模式，隔离外部
SiliconFlow API 与 Qdrant 服务端；真实 SiliconFlow 向量化在 ``scripts/`` 冒烟中验证。
"""

from __future__ import annotations

import json

from backend.app.rag import KnowledgeIngestor, KnowledgeRetriever, split_text
from backend.app.repositories import KnowledgeDocumentRepository
from backend.app.tools import build_knowledge_search_tool
from backend.tests._fakes import FakeEmbedding, make_in_memory_store


def test_split_text_empty() -> None:
    assert split_text("") == []
    assert split_text("   \n\n   ") == []


def test_split_text_short() -> None:
    assert split_text("hello world", chunk_size=100) == ["hello world"]


def test_split_text_long_with_overlap() -> None:
    text = "a" * 250
    chunks = split_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_split_text_multi_paragraph() -> None:
    text = "第一段\n\n第二段\n\n第三段"
    chunks = split_text(text, chunk_size=100)
    assert len(chunks) == 1
    assert "第一段" in chunks[0]


async def test_ingest_and_retrieve_roundtrip(session_factory) -> None:
    store = await make_in_memory_store()
    ingestor = KnowledgeIngestor(
        session_factory, FakeEmbedding(), store, chunk_size=200, chunk_overlap=20
    )
    await ingestor.ingest_document(
        document_id="doc-001",
        title="上游超时排查",
        source="ops-manual",
        content="上游服务超时通常由网络抖动或下游负载过高导致。排查时先看 error 字段。",
        document_type="md",
    )

    retriever = KnowledgeRetriever(FakeEmbedding(), store)
    hits = await retriever.retrieve("超时 排查", top_k=3)
    assert hits
    assert hits[0].document_id == "doc-001"
    assert hits[0].title == "上游超时排查"
    assert hits[0].source == "ops-manual"

    async with session_factory() as session:
        doc = await KnowledgeDocumentRepository(session).get_by_document_id("doc-001")
        assert doc is not None
        assert doc.title == "上游超时排查"


async def test_metadata_filtering(session_factory) -> None:
    store = await make_in_memory_store()
    ingestor = KnowledgeIngestor(
        session_factory, FakeEmbedding(), store, chunk_size=200, chunk_overlap=20
    )
    await ingestor.ingest_document(
        document_id="doc-md",
        title="文档A",
        source="s1",
        content="这是关于超时错误的说明，网络抖动会导致上游超时。",
        document_type="md",
    )
    await ingestor.ingest_document(
        document_id="doc-txt",
        title="文档B",
        source="s2",
        content="这是另一份纯文本说明，也提到超时错误的排查。",
        document_type="txt",
    )

    retriever = KnowledgeRetriever(FakeEmbedding(), store)
    hits = await retriever.retrieve("超时", top_k=10, document_type="md")
    assert hits
    assert all(h.document_type == "md" for h in hits)


async def test_knowledge_search_tool(session_factory) -> None:
    store = await make_in_memory_store()
    ingestor = KnowledgeIngestor(
        session_factory, FakeEmbedding(), store, chunk_size=200, chunk_overlap=20
    )
    await ingestor.ingest_document(
        document_id="doc-001",
        title="成本优化",
        source="cost-guide",
        content="Token 成本过高时，可精简提示词、控制上下文长度、选用更便宜的模型。",
        document_type="md",
    )

    retriever = KnowledgeRetriever(FakeEmbedding(), store)
    tool = build_knowledge_search_tool(retriever)
    output = await tool.ainvoke({"query": "成本优化", "top_k": 2})
    data = json.loads(output)
    assert data["query"] == "成本优化"
    assert data["hits"]
    assert data["hits"][0]["source"] == "cost-guide"
