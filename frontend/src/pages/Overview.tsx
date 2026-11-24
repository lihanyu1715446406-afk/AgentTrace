import { Alert, Card, Col, Row, Spin, Statistic, Table, Tag } from "antd";
import ReactECharts from "echarts-for-react";
import { useAsync } from "../hooks/useAsync";
import { apiGet } from "../api/client";
import type { Overview as OverviewData, RecentTrace } from "../types";

function fmtTime(v: string): string {
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString();
}

export default function Overview() {
  const { data, loading, error } = useAsync<OverviewData>(() =>
    apiGet<OverviewData>("/overview")
  );

  if (loading) return <Spin style={{ display: "block", marginTop: 80 }} />;
  if (error) return <Alert type="error" message="加载失败" description={error} />;
  if (!data) return null;

  const pie = {
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        type: "pie",
        radius: ["40%", "65%"],
        data: data.cost_by_model.map((m) => ({
          name: m.model_name,
          value: m.total_tokens,
        })),
      },
    ],
  };

  const columns = [
    { title: "Trace ID", dataIndex: "trace_id", key: "trace_id" },
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
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="Trace 总数" value={data.total_traces} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败 Trace"
              value={data.failed_traces}
              valueStyle={{ color: "#cf1322" }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Span 总数" value={data.total_spans} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="项目数" value={data.total_projects} />
          </Card>
        </Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="Token 总数" value={data.total_tokens} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总成本(USD)"
              value={data.total_cost ?? 0}
              precision={8}
            />
          </Card>
        </Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={10}>
          <Card title="各模型 Token 占比">
            <ReactECharts option={pie} style={{ height: 320 }} />
          </Card>
        </Col>
        <Col span={14}>
          <Card title="最近 Trace">
            <Table<RecentTrace>
              rowKey="trace_id"
              columns={columns}
              dataSource={data.recent_traces}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
