import { Alert, Card, Spin, Table, Tag } from "antd";
import { useAsync } from "../hooks/useAsync";
import { apiGet } from "../api/client";
import type { KnowledgeDocumentRead } from "../types";

function fmtTime(v: string): string {
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString();
}

export default function Knowledge() {
  const { data, loading, error } = useAsync<KnowledgeDocumentRead[]>(() =>
    apiGet<KnowledgeDocumentRead[]>("/knowledge")
  );

  if (loading) return <Spin style={{ display: "block", marginTop: 80 }} />;
  if (error) return <Alert type="error" message="加载失败" description={error} />;
  if (!data) return null;

  const columns = [
    { title: "文档 ID", dataIndex: "document_id", key: "document_id" },
    { title: "标题", dataIndex: "title", key: "title" },
    { title: "来源", dataIndex: "source", key: "source" },
    {
      title: "类型",
      dataIndex: "document_type",
      key: "document_type",
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: "入库时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => fmtTime(v),
    },
  ];

  return (
    <Card title="知识库">
      <Table<KnowledgeDocumentRead>
        rowKey="document_id"
        columns={columns}
        dataSource={data}
        pagination={{ pageSize: 20 }}
        size="small"
      />
    </Card>
  );
}
