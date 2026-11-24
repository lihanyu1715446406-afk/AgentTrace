import { Alert, Card, Descriptions, Spin, Table, Tag } from "antd";
import { useAsync } from "../hooks/useAsync";
import { apiGet } from "../api/client";
import type { EvaluationDataset, EvalSample } from "../types";

export default function Evaluation() {
  const { data, loading, error } = useAsync<EvaluationDataset>(() =>
    apiGet<EvaluationDataset>("/evaluation/dataset")
  );

  if (loading) return <Spin style={{ display: "block", marginTop: 80 }} />;
  if (error) return <Alert type="error" message="加载失败" description={error} />;
  if (!data) return null;

  const metricItems = Object.entries(data.metrics).map(([k, v]) => ({
    key: k,
    label: k,
    children: v,
  }));

  const columns = [
    { title: "样本 ID", dataIndex: "sample_id", key: "sample_id" },
    { title: "提问", dataIndex: "query", key: "query" },
    {
      title: "期望任务类型",
      dataIndex: "expected_task_type",
      key: "expected_task_type",
      render: (t: string | null) => (t ? <Tag color="blue">{t}</Tag> : "-"),
    },
    {
      title: "期望工具",
      dataIndex: "expected_tool_names",
      key: "expected_tool_names",
      render: (tools: string[]) => tools.map((t) => <Tag key={t}>{t}</Tag>),
    },
    {
      title: "关键事实",
      dataIndex: "expected_facts",
      key: "expected_facts",
      render: (facts: string[]) => facts.join("、") || "-",
    },
  ];

  return (
    <div>
      <Card title="评估指标" style={{ marginBottom: 16 }}>
        <Descriptions bordered column={1} size="small" items={metricItems} />
      </Card>
      <Card title={`标准测试集（${data.dataset_name}）`}>
        <Table<EvalSample>
          rowKey="sample_id"
          columns={columns}
          dataSource={data.samples}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
}
