# AgentTrace 项目开发进度

> 依据：v2.0 第二十一章 21.5，每次开发结束必须更新本文件。

## 当前状态

- **当前里程碑**：M8（MCP + 工程化）——✅ 验收通过（ruff + pytest 已通过）
- **整体阶段**：M0~M8 全部完成，项目收官；5 项遗留优化全部完成并验证（后端 ruff/pytest/mypy 全绿 + 前端构建通过 + pre-commit 已装）
- **最后更新**：2026-11-20

## 里程碑进度

| 里程碑 | 主题 | 状态 |
|---|---|---|
| M0 | 项目初始化与架构设计 | ✅ 已完成（验收通过） |
| M1 | 单 Agent + Tool Calling | ✅ 已完成（验收通过） |
| M2 | Planning | ✅ 已完成（验收通过） |
| M3 | Multi-Agent | ✅ 已完成（验收通过） |
| M4 | RAG | ✅ 已完成（验收通过） |
| M5 | Memory | ✅ 已完成（验收通过） |
| M6 | Reflection + Evaluation | ✅ 已完成（验收通过） |
| M7 | SDK 与数据采集 | ✅ 已完成（验收通过） |
| M8 | MCP + 工程化 | ✅ 已完成（验收通过） |

## M5 验收结果（ruff + pytest 已通过）

| 验收项 | 结果 |
|---|---|
| Checkpointer（短期记忆/中断恢复） | ✅ `WorkingMemory` + `interrupt`/`Command(resume)`；生产用 `AsyncPostgresSaver`，测试用 `InMemorySaver` |
| Working Memory | ✅ LangGraph State + Checkpointer（`memory/working.py`） |
| Episodic / Semantic Memory | ✅ 共用 `MemoryRecord` 表，`MemoryType` 区分（EPISODIC/SEMANTIC/PROCEDURAL） |
| 检索 | ✅ `MemoryManager.recall`（project + 类型 + PG `ILIKE` 关键词） |
| 更新 | ✅ `MemoryManager.update` |
| 去重 | ✅ 写入前精确内容匹配，命中则更新而非新增 |
| 巩固 | ✅ `MemoryManager.consolidate`（LLM 把 episodic 提炼成 semantic；`distill` 注入点隔离 LLM） |
| Agent 在新任务中检索历史经历 | ✅ `memory_search` 只读工具 + `ToolRegistry` 可选 `memory_tool` |
| `uv run pytest` 全绿 | ✅ 41 passed（33 旧 + 8 新），2 warnings（M1 `create_react_agent` 弃用） |
| `uv run ruff check` | ✅ All checks passed |
| 学习文档 07 产出 | ✅ 见下文 |

## M5 完成内容

- **短期记忆（Working + Checkpointer）** `backend/app/memory/working.py`：`WorkingMemory` 封装「analyze → confirm（`interrupt`）→ finalize」三节点图，`start` 停在人工确认点、`resume` 用同一 `thread_id` 恢复；体现 ADR-0004「Human-in-the-loop」。
- **Checkpointer 配置** `backend/app/memory/checkpoint.py`：`get_checkpoint_conn_string()`（psycopg 连接串，复用全局 PG 配置）+ `build_in_memory_checkpointer()`（测试用）。
- **长期记忆管理** `backend/app/memory/manager.py`：`MemoryManager` 提供 `record`（去重）、`recall`（ILIKE 检索）、`update`、`consolidate`（LLM 巩固）；`distill` 注入点隔离 LLM。
- **数据访问** `backend/app/repositories/memory_record_repository.py`：`MemoryRecordRepository`（add/get/list_by_project/find_duplicate/search）。
- **结构化模型** `backend/app/schemas/memory.py`：`MemoryType` / `MemoryRecordRead` / `MemoryWriteResult` / `MemorySearchResult` / `ConsolidationDraft` / `ConsolidationResult` / `WorkingSnapshot`。
- **检索工具** `backend/app/tools/memory_tools.py`：`build_memory_search_tool`（只读 `memory_search`）；`tools/base.py` 的 `ToolRegistry` 加可选 `memory_tool`。
- **脚本** `scripts/memory_demo.py`（长期记忆全流程 + Agent 检索）、`scripts/memory_checkpoint_demo.py`（PG 持久化中断恢复）。
- **依赖** `pyproject.toml` 加 `langgraph-checkpoint-postgres>=2.0`（生产 PG checkpointer）。
- **测试** `backend/tests/test_memory.py`（8）：写入/去重、关键词+类型检索、更新、巩固（distill 注入）、无情景记忆跳过、memory_search 工具、中断恢复（确认 + 拒绝）。
- **代码质量**：修复 isort（`schemas/__init__.py` 的 memory 排序）、UP040（`DistillFunc` 用 PEP 695 `type` 别名）、State 定义不加 `from __future__ import annotations`。

## M6 验收结果（ruff + pytest 已通过）

| 验收项 | 结果 |
|---|---|
| 证据检查（识别缺证据结论） | ✅ `Reflector.reflect` 逐条结论 vs 工具数据，判定 `EvidenceStatus`（SUPPORTED/MISSING/CONTRADICTED/UNVERIFIABLE） |
| 一致性检查 | ✅ `Reflector` 检查结论间矛盾（`ConsistencyIssue`） |
| 有限重分析 | ✅ `ReflectiveDiagnoser`：`needs_reanalysis` + `max_reflections` 双条件控制循环 |
| 标准测试集 | ✅ `STANDARD_DATASET`（4 条样本，基于 seed 演示数据） |
| 自动化评估 | ✅ `Evaluator.evaluate`：task_type_accuracy / tool_coverage / fact_coverage / passed |
| LLM-as-a-Judge | ✅ `build_llm_judge`（`_JudgeVerdict` 结构化输出） |
| `uv run pytest` 全绿 | ✅ 51 passed（41 旧 + 10 新），2 warnings（M1 `create_react_agent` 弃用） |
| `uv run ruff check` | ✅ All checks passed |
| 学习文档 08/09 产出 | ✅ 见下文 |

## M6 完成内容

- **反思（Reflection）** `backend/app/reflection/reflector.py`：`Reflector` 对 `SupervisorResult` 逐条结论做证据检查（`ClaimCheck` + 四态 `EvidenceStatus`）+ 一致性检查（`ConsistencyIssue`）；`judge`/`consistency_checker` 注入点隔离 LLM。
- **有限重分析** `backend/app/reflection/reflective_agent.py`：`ReflectiveDiagnoser` 包装诊断函数，`needs_reanalysis` + `max_reflections` 控制循环。
- **评估（Evaluation）** `backend/app/evaluation/evaluator.py`：`Evaluator.evaluate` 算 task_type_accuracy / tool_coverage / fact_coverage / passed；`build_llm_judge` 提供 LLM-as-judge。
- **标准测试集** `backend/app/evaluation/dataset.py`：`STANDARD_DATASET`（4 条样本）。
- **结构化模型** `backend/app/schemas/reflection.py`（`EvidenceStatus`/`ClaimCheck`/`ConsistencyIssue`/`ReflectionResult`/`ReflectiveResult`）、`backend/app/schemas/evaluation.py`（`EvalSample`/`CaseOutput`/`EvalCaseResult`/`EvalReport`）。
- **脚本** `scripts/reflection_demo.py`（真实 LLM 反思 + 重分析）、`scripts/eval_demo.py`（真实 LLM 评估）。
- **测试** `backend/tests/test_reflection.py`（6）、`backend/tests/test_evaluation.py`（4）。

## M7 验收结果（ruff + pytest 已通过）

| 验收项 | 结果 |
|---|---|
| Python SDK | ✅ `sdk/agenttrace/`（`AgentTraceClient` / `Tracer` / `Trace` / `Span`） |
| Trace/Span 管理 | ✅ `Tracer.start_trace/end_trace/start_span/end_span` |
| 父子关系 | ✅ `Span.parent_span_id` + contextvars 自动挂父 Span |
| Token 记录 | ✅ `Span.record_token_usage` → 上报汇总 → `TokenUsage` |
| 异步上报 | ✅ `AgentTraceClient.flush`（httpx AsyncClient） |
| LangGraph 集成 | ✅ `TraceCallbackHandler`（on_llm_start/end + on_tool_start/end） |
| 鉴权 | ✅ `IngestService`（sha256 + `compare_digest`，只存哈希） |
| 采集展示闭环 | ✅ `POST /ingest/trace` + `GET /traces`（复用只读 Repository） |
| `uv run pytest` | ✅ 60 passed（51 旧 + 9 新） |
| `uv run ruff check` | ✅ All checks passed |
| 学习文档 10 产出 | ✅ 见下文 |

## M7 完成内容

- **Python SDK** `sdk/agenttrace/`：`client.py`（`AgentTraceClient`：flush/list_traces/get_trace）、`trace.py`（`Trace`）、`span.py`（`Span` + `record_token_usage`）、`tracer.py`（`Tracer`：上下文管理器 + 装饰器）、`context.py`（`_current_trace`/`_current_span` 两个 contextvars）、`langgraph.py`（`TraceCallbackHandler`）、`exporters/http.py`（`HTTPExporter`）。
- **后端采集链路**：`schemas/ingest.py`（`TraceIngest`/`SpanIngest`/`TokenUsageIngest`/`IngestResult`/`ProjectCreate` 等）→ `services/ingest_service.py`（`IngestService`：`create_project`/`authenticate`/`ingest`；sha256 + `compare_digest`）→ `repositories/ingest_repository.py`（`IngestRepository` 写入）→ `api/routes/{ingest,projects,traces}.py` + `api/dependencies.py`（`authenticate_project`）。
- **路由**：`POST /projects`（建项目 + 一次性返回明文 Key）、`POST /ingest/trace`（上报）、`GET /traces`、`GET /traces/{trace_id}`（展示）。
- **测试** `backend/tests/test_sdk.py`（5：父子关系/token/同步装饰器/异步装饰器 flush/payload）、`backend/tests/test_ingest.py`（4：哈希存储/落库+父子+token/坏 key 拒绝/未知项目拒绝）。
- **脚本** `scripts/sdk_demo.py`：真实 LangGraph Agent（`create_react_agent` + `TraceCallbackHandler`）采集 → 上报 → 查询展示真实数据。
- **依赖** `pyproject.toml`：`httpx` 从 dev 组提升为主依赖（SDK 运行时上报需要）。
- **ADR**：ADR-0006（SDK 走 HTTP 上报，不直连 DB）、ADR-0007（API Key sha256 + `compare_digest`）已写入 `系统架构设计.md`。

## M8 验收结果（ruff + pytest 已通过）

| 验收项 | 结果 |
|---|---|
| MCP Server | ✅ `mcp_server/server.py`：`MCPServer("AgentTrace")` + `@mcp.tool()` 注册 3 个只读工具（已迁移到 mcp 2.x API） |
| MCP Tools | ✅ `trace_query` / `span_query` / `cost_analysis`，复用 M1 `query_trace`/`query_span`/`analyze_cost`，语义单源 |
| MCP Client 可调用工具 | ✅ `scripts/mcp_client_demo.py`（stdio 连接 + `list_tools` + `call_tool`） |
| REST API 完善 | ✅ 新增 `GET /overview`、`GET /projects`、`POST /diagnose`、`GET /knowledge`、`GET /evaluation/dataset` |
| 鉴权 | ✅ M7 已实现：`X-API-Key` + `project_id` 匹配（sha256 + `compare_digest`） |
| React Dashboard | ✅ `frontend/`（Vite+React+TS+AntD+ECharts，6 页：总览/Trace 浏览器/Trace 详情/AI 诊断/知识库/评估） |
| Docker | ✅ `backend/Dockerfile` + `frontend/Dockerfile` + `frontend/nginx.conf` + `docker-compose.yml`（postgres/qdrant/backend/frontend） |
| Docker 一键部署运行 | ✅ `docker compose up -d --build` 四容器全 Up；后端迁移成功 + `GET /health` → `{"status":"ok"}` |
| 集成测试 | ✅ `backend/tests/test_api.py`（ASGI + 依赖覆盖，3→5 个）；`test_mcp.py`（5 个） |
| README | ✅ 完善部署/SDK/MCP/API/测试说明 |
| 学习文档 11/12/13 | ✅ 见下文 |
| `uv run pytest` | ✅ 70 passed（2 warnings：M1 `create_react_agent` 弃用） |
| `uv run ruff check` | ✅ All checks passed |

## M8 完成内容

- **MCP Server + 工具** `mcp_server/server.py`：`query_trace`/`query_span`/`analyze_cost` 三个实现（复用 `TraceRepository`/`SpanRepository`/`TokenUsageRepository`）+ `build_server(session_factory=None)` 工厂 + `@mcp.tool()` 注册 + stdio 入口。已从 v1 `FastMCP` 迁移到 mcp 2.x `MCPServer`（`from mcp.server.mcpserver import MCPServer`）。
- **MCP Client 冒烟** `scripts/mcp_client_demo.py`：stdio 拉起 `mcp_server.server`，`initialize → list_tools → call_tool`。
- **REST API 完善**：`routes/overview.py`（`GET /overview`）、`routes/projects.py`（`GET /projects`）、`routes/diagnose.py`（`POST /diagnose`，Multi-Agent）、`routes/knowledge.py`（`GET /knowledge`）、`routes/evaluation.py`（`GET /evaluation/dataset`）；新增 `OverviewRepository.summary()`、`ProjectRepository.list()`、`schemas/{overview,rag,evaluation}` 相关模型、`dependencies.get_llm_dependency/get_tools_dependency`。
- **React Dashboard** `frontend/`：Vite+React+TS+AntD+ECharts，6 页全部对接真实 REST 接口；`api/client.ts`（fetch 封装）、`apiKey.ts`（localStorage 存 project_id + API Key）、`hooks/useAsync.ts`。
- **Docker**：`backend/Dockerfile`（uv sync → alembic → uvicorn）、`frontend/Dockerfile`（node 构建 → nginx）、`frontend/nginx.conf`（SPA 回退 + API 反代）、`docker-compose.yml`（四服务）、`.dockerignore`。
- **测试** `backend/tests/test_api.py`（新增 `test_list_knowledge`、`test_evaluation_dataset`）、`backend/tests/test_mcp.py`（迁移到 `await server.list_tools()`）。
- **依赖** `pyproject.toml`：`mcp>=1.0`（解析到 mcp 2.3.0）。

## 遗留优化项（依次优化，2026-11-20）

对 M0~M8 收官后遗留的 5 个优化项依次处理（代码 + 后端回归验证已完成）：

| # | 优化项 | 状态 |
|---|---|---|
| 1 | `create_react_agent` → `langchain.agents.create_agent` | ✅ 代码 + 文档已改（`react_agent.py`、`scripts/sdk_demo.py`、`test_react_agent.py`、docs 02/03） |
| 2 | project_id「名称 vs UUID」解析 | ✅ `ProjectRepository.resolve()` + `trace_tools.py`/`cost_tools.py`/`mcp_server/server.py` + 6 个测试 |
| 3 | RAG/Memory 语义检索 + 语义去重 | ✅ `MemoryManager` 语义模式 + `memory/factory.py` + `tests/_fakes.py` + 3 个语义记忆测试；docs 07 已更新 |
| 4 | 前端 chunk 分割 | ✅ 路由级 `React.lazy` + `vite.config.ts` `manualChunks`（react/antd/echarts）；`npm run build` 通过，拆成 6 页面 chunk + 3 vendor chunk，主入口 11.6 kB |
| 5 | `pre-commit install` + `mypy` 校验 | ✅ `pre-commit` 加入 dev 依赖、`[tool.mypy]` 加 `files`；mypy 31 错误已清零（0 errors）；`git init` + `pre-commit install` 已装到 `.git/hooks/pre-commit` |

## 已知问题

- **检索质量随查询措辞波动**（M4/M6 遗留）：语义检索缓解但未根治，M6 用 Recall@K 量化。
- **语义记忆模式未经真实环境冒烟**：`build_semantic_memory_manager` 依赖真实 SiliconFlow embedding + Qdrant，测试用 `tests/_fakes.py` 隔离；真实链路待冒烟脚本验证。
- Docker 构建的「load metadata」阶段不走 Docker Desktop 代理、会直连污染 IP（daemon `docker pull` 正常）：本次用「先 `docker pull` 预拉基础镜像，再 build」绕开。

## 下一步

- M0~M8 已全部完成并验收通过，项目收官；5 项遗留优化全部完成并验证。
- 后端回归验证 ✅：`uv run ruff check`（All checks passed）、`uv run pytest`（79 passed）、`uv run mypy`（0 errors，133 files）。
- 前端构建验证 ✅：`cd frontend && npm run build`（8.38s，3630 modules；拆成 6 页面 chunk + react/antd/echarts 3 个 vendor chunk，主入口 11.6 kB）。
- pre-commit ✅：`git init` + `uv run pre-commit install` 已装到 `.git/hooks/pre-commit`；`uv run pre-commit run --all-files` 三 hook（ruff / ruff-format / mypy）全 Passed。
- 换行符统一 ✅：新增 `.gitattributes`（`* text=auto eol=lf`），消掉 Windows `git add` 的 CRLF 警告。

## 对应学习文档

- 规划文档：`docs/00-项目规划/`。
- 学习文档（15 要素格式）：`docs/02-Agent基础`、`docs/03-Tool-Calling`、`docs/04-Planning`、`docs/05-Multi-Agent`、`docs/06-RAG`、`docs/07-Memory`、`docs/08-Reflection`、`docs/09-Evaluation`、`docs/10-SDK与数据采集`、`docs/11-MCP`、`docs/12-工程化`、`docs/13-项目源码解析`。
