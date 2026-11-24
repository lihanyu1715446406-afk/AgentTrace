import { useEffect, useState } from "react";
import { Alert, Button, Card, Input, Select, Space, Table, Tag } from "antd";
import { Link } from "react-router-dom";
import { apiGet } from "../api/client";
import {
  getApiKey,
  getProjectId,
  setApiKey,
  setProjectId,
} from "../apiKey";
import type { ProjectRead, TraceSummary } from "../types";

function fmtTime(v: string): string {
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString();
}

export default function TraceExplorer() {
  const [projects, setProjects] = useState<ProjectRead[]>([]);
  const [projectId, setProjectIdState] = useState<string>(getProjectId());
  const [apiKey, setApiKeyState] = useState<string>(getApiKey());
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ProjectRead[]>("/projects")
      .then(setProjects)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const loadTraces = () => {
    if (!projectId || !apiKey) {
      setError("请先选择项目并填写 API Key");
      return;
    }
    setProjectId(projectId);
    setApiKey(apiKey);
    setLoading(true);
    setError(null);
    apiGet<TraceSummary[]>(
      `/traces?project_id=${encodeURIComponent(projectId)}`,
      { "X-API-Key": apiKey }
    )
      .then(setTraces)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  const columns = [
    {
      title: "Trace ID",
      dataIndex: "trace_id",
      key: "trace_id",
      render: (v: string) => <Link to={`/traces/${v}`}>{v}</Link>,
    },
    { title: "名称", dataIndex: "name", key: "name" },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => (
        <Tag color={s === "success" ? "green" : "red"}>{s}</Tag>
      ),
    },
    {
      title: "开始时间",
      dataIndex: "started_at",
      key: "started_at",
      render: (v: string) => fmtTime(v),
    },
    { title: "耗时(ms)", dataIndex: "duration_ms", key: "duration_ms" },
  ];

  return (
    <Card title="Trace 浏览器">
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="选择项目"
          style={{ width: 240 }}
          value={projectId || undefined}
          onChange={(v: string) => setProjectIdState(v)}
          options={projects.map((p) => ({
            value: p.project_id,
            label: `${p.name} (${p.project_id.slice(0, 8)}…)`,
          }))}
        />
        <Input.Password
          placeholder="项目 API Key（创建项目时返回的一次性明文 Key）"
          value={apiKey}
          onChange={(e) => setApiKeyState(e.target.value)}
          style={{ width: 380 }}
        />
        <Button type="primary" loading={loading} onClick={loadTraces}>
          加载 Traces
        </Button>
      </Space>
      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}
      <Table<TraceSummary>
        rowKey="trace_id"
        columns={columns}
        dataSource={traces}
        pagination={{ pageSize: 20 }}
        size="small"
      />
    </Card>
  );
}
