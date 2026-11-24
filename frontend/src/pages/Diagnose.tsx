import { useState } from "react";
import { Alert, Button, Card, Input, Space, Spin, Tag, Typography } from "antd";
import { apiPost } from "../api/client";
import type { SupervisorResult } from "../types";

const { Paragraph, Text } = Typography;

export default function Diagnose() {
  const [query, setQuery] = useState<string>("");
  const [result, setResult] = useState<SupervisorResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = () => {
    if (!query.trim()) {
      setError("请输入诊断问题");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    apiPost<SupervisorResult>("/diagnose", { query: query.trim() })
      .then(setResult)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  };

  return (
    <Card title="AI 诊断">
      <Space direction="vertical" style={{ width: "100%" }}>
        <Input.TextArea
          rows={3}
          placeholder="例如：分析 trace tr-demo-001 为什么失败"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Button type="primary" loading={loading} onClick={run}>
          开始诊断
        </Button>
      </Space>

      {loading && <Spin style={{ display: "block", marginTop: 24 }} />}
      {error && <Alert type="error" message={error} style={{ marginTop: 16 }} />}

      {result && (
        <div style={{ marginTop: 24 }}>
          <Space wrap style={{ marginBottom: 16 }}>
            <Text strong>任务类型：</Text>
            <Tag color="blue">{result.task_type ?? "未知"}</Tag>
            <Text strong>调度角色：</Text>
            {result.assigned_roles.map((r) => (
              <Tag key={r}>{r}</Tag>
            ))}
          </Space>

          {result.analysis_results.map((a) => (
            <Card
              key={a.role}
              size="small"
              title={`${a.role} 分析`}
              style={{ marginBottom: 12 }}
            >
              <Paragraph>{a.summary}</Paragraph>
              <ul>
                {a.findings.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              {a.error && <Alert type="warning" message={a.error} />}
            </Card>
          ))}

          <Card size="small" title="最终报告">
            <Paragraph style={{ whiteSpace: "pre-wrap" }}>
              {result.final_report}
            </Paragraph>
          </Card>
        </div>
      )}
    </Card>
  );
}
