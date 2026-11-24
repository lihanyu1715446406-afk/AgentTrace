import { Alert, Card, Descriptions, Spin, Table, Tag } from "antd";
import { useParams } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { apiGet } from "../api/client";
import { getApiKey, getProjectId } from "../apiKey";
import type { SpanDetail, TraceDetailResponse } from "../types";

function fmtTime(v: string): string {
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString();
}

function fmtJson(v: unknown): string {
  if (v === null || v === undefined) return "-";
  const s = JSON.stringify(v);
  return s.length > 200 ? `${s.slice(0, 200)}…` : s;
}

export default function TraceDetail() {
  const { traceId = "" } = useParams();
  const { data, loading, error } = useAsync<TraceDetailResponse>(() =>
    apiGet<TraceDetailResponse>(
      `/traces/${traceId}?project_id=${encodeURIComponent(getProjectId())}`,
      {
        "X-API-Key": getApiKey(),
      }
    )
  );

  if (loading) return <Spin style={{ display: "block", marginTop: 80 }} />;
  if (error) return <Alert type="error" message="加载失败" description={error} />;
  if (!data) return null;

  const spanColumns = [
    { title: "Span ID", dataIndex: "span_id", key: "span_id" },
    { title: "父 Span", dataIndex: "parent_span_id", key: "parent_span_id" },
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "类型", dataIndex: "span_type", key: "span_type" },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (s: string) => (
        <Tag color={s === "success" ? "green" : s === "error" ? "red" : "blue"}>
          {s}
        </Tag>
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

  const usageColumns = [
    { title: "模型", dataIndex: "model_name", key: "model_name" },
    { title: "Prompt Tokens", dataIndex: "prompt_tokens", key: "prompt_tokens" },
    {
      title: "Completion Tokens",
      dataIndex: "completion_tokens",
      key: "completion_tokens",
    },
    { title: "总 Tokens", dataIndex: "total_tokens", key: "total_tokens" },
    { title: "成本", dataIndex: "estimated_cost", key: "estimated_cost" },
  ];

  return (
    <div>
      <Card title="Trace 详情" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="Trace ID">{data.trace.trace_id}</Descriptions.Item>
          <Descriptions.Item label="名称">{data.trace.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={data.trace.status === "success" ? "green" : "red"}>
              {data.trace.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="耗时(ms)">
            {data.trace.duration_ms ?? "-"}
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {fmtTime(data.trace.started_at)}
          </Descriptions.Item>
          <Descriptions.Item label="结束时间">
            {data.trace.ended_at ? fmtTime(data.trace.ended_at) : "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Span 列表" style={{ marginBottom: 16 }}>
        <Table<SpanDetail>
          rowKey="span_id"
          columns={spanColumns}
          dataSource={data.spans}
          pagination={false}
          size="small"
          expandable={{
            expandedRowRender: (span) => (
              <div>
                <p>
                  <b>input:</b> {fmtJson(span.input)}
                </p>
                <p>
                  <b>output:</b> {fmtJson(span.output)}
                </p>
                <p>
                  <b>error:</b> {fmtJson(span.error)}
                </p>
              </div>
            ),
          }}
        />
      </Card>

      <Card title="Token 用量" style={{ marginBottom: 16 }}>
        <Table
          rowKey={(u) => u.model_name}
          columns={usageColumns}
          dataSource={data.token_usages}
          pagination={false}
          size="small"
        />
      </Card>

      <Card title="成本汇总">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="总 Prompt Tokens">
            {data.cost.total_prompt_tokens}
          </Descriptions.Item>
          <Descriptions.Item label="总 Completion Tokens">
            {data.cost.total_completion_tokens}
          </Descriptions.Item>
          <Descriptions.Item label="总 Tokens">
            {data.cost.total_tokens}
          </Descriptions.Item>
          <Descriptions.Item label="总成本(USD)">
            {data.cost.total_cost ?? "-"}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
