# MCP Server

把 AgentTrace 的只读诊断工具以 **MCP（Model Context Protocol）** 协议开放，供其他 Agent / MCP Client 调用。

## 工具

| 工具名 | 作用 | 参数 |
|---|---|---|
| `trace_query` | 查单条 trace 详情 / 列项目 trace 列表 | `trace_id` / `project_id` / `limit` |
| `span_query` | 查单条 span / 列某 trace 全部 span | `span_id` / `trace_id` / `limit` |
| `cost_analysis` | 按项目 / 轨迹聚合 token 与成本 | `project_id` / `trace_id` |

三个工具均**只读**（符合第一阶段「诊断工具只读」边界），返回与 M1 LangChain 工具一致的 JSON 字符串。

## 启动（stdio）

```bash
uv run python -m mcp_server.server
```

MCP Client（如 Claude Desktop / 任意 MCP SDK）通过 stdio 连接即可。演示脚本：`scripts/mcp_client_demo.py`。
