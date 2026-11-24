"""M8 REST API 集成测试：项目列表、Overview 聚合、AI 诊断接口。

通过 ``httpx.ASGITransport`` 走真实 FastAPI 应用，并用 ``dependency_overrides`` 把
LLM / 工具 / DB 会话注入隔离库或假模型，避免依赖真实 DeepSeek 与生产库。
"""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage

from backend.app.api import dependencies
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models import KnowledgeDocument
from backend.app.schemas.multi_agent import AnalysisDraft, AnalyzerRole, SupervisorDecision
from backend.app.schemas.planning import Intent, TaskType
from backend.app.tools import ToolRegistry


class _FixedRunnable:
    """返回固定对象的 Runnable 替身。"""

    def __init__(self, output):
        self._output = output

    async def ainvoke(self, *args, **kwargs):
        return self._output


class _PopRunnable:
    """每次弹出列表下一个对象的 Runnable 替身。"""

    def __init__(self, items):
        self._items = list(items)

    async def ainvoke(self, *args, **kwargs):
        return self._items.pop(0)


class _FakeLLM:
    """假模型：按 schema 类型返回固定意图/决策/分析草稿，``ainvoke`` 返回固定报告。"""

    def __init__(self, intent, decision, drafts, report):
        self._intent = intent
        self._decision = decision
        self._drafts = list(drafts)
        self._report = report

    def with_structured_output(self, schema, **kwargs):
        if schema is Intent:
            return _FixedRunnable(self._intent)
        if schema is SupervisorDecision:
            return _FixedRunnable(self._decision)
        if schema is AnalysisDraft:
            return _PopRunnable(self._drafts)
        raise AssertionError(f"unexpected schema: {schema}")

    async def ainvoke(self, messages, **kwargs):
        return AIMessage(content=self._report)


def _override_get_db(factory):
    """把全局 ``get_db`` 覆盖为指向测试库会话工厂的异步生成器依赖。"""

    async def _get_db():
        async with factory() as session:
            yield session

    return _get_db


async def test_list_projects(seeded, session_factory):
    app.dependency_overrides[get_db] = _override_get_db(session_factory)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["project_id"] == seeded["project_id"]
        assert data[0]["name"] == "test-project"
    finally:
        app.dependency_overrides.clear()


async def test_overview_endpoint(seeded, session_factory):
    app.dependency_overrides[get_db] = _override_get_db(session_factory)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_traces"] == 2
        assert data["failed_traces"] == 1
        assert data["total_spans"] == 2
        assert data["total_projects"] == 1
        assert data["total_tokens"] == 650
        assert data["total_cost"] is not None
        assert len(data["recent_traces"]) == 2
    finally:
        app.dependency_overrides.clear()


async def test_list_knowledge(session_factory):
    async with session_factory() as session:
        session.add(
            KnowledgeDocument(
                document_id="doc-test-001",
                title="测试文档",
                source="test.md",
                content="正文",
                document_type="md",
            )
        )
        await session.commit()
    app.dependency_overrides[get_db] = _override_get_db(session_factory)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["document_id"] == "doc-test-001"
        assert data[0]["title"] == "测试文档"
        assert data[0]["created_at"] is not None
    finally:
        app.dependency_overrides.clear()


async def test_evaluation_dataset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/evaluation/dataset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_name"] == "standard"
    assert len(data["samples"]) == 4
    assert "task_type_accuracy" in data["metrics"]


async def test_diagnose_endpoint(seeded, session_factory):
    fake = _FakeLLM(
        Intent(task_type=TaskType.TRACE_ANALYSIS, trace_id=seeded["trace_id"]),
        SupervisorDecision(assigned_roles=[AnalyzerRole.TRACE], reasoning="只查 trace"),
        [AnalysisDraft(summary="结构正常", findings=["含 1 个 span"])],
        "诊断报告。",
    )
    app.dependency_overrides[dependencies.get_llm_dependency] = lambda: fake
    app.dependency_overrides[dependencies.get_tools_dependency] = lambda: ToolRegistry(
        session_factory
    ).build_all()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/diagnose", json={"query": "分析这条 trace"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_type"] == "trace_analysis"
        assert data["assigned_roles"] == ["trace"]
        assert data["final_report"] == "诊断报告。"
        assert len(data["analysis_results"]) == 1
    finally:
        app.dependency_overrides.clear()
