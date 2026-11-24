import { lazy, Suspense } from "react";
import { Layout, Menu, Spin, Typography } from "antd";
import {
  ApartmentOutlined,
  BookOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import { Link, Route, Routes, useLocation } from "react-router-dom";

// 按路由懒加载页面：首屏只下载总览，其余页面（及其依赖，如 echarts）按需加载。
const Overview = lazy(() => import("./pages/Overview"));
const TraceExplorer = lazy(() => import("./pages/TraceExplorer"));
const TraceDetail = lazy(() => import("./pages/TraceDetail"));
const Diagnose = lazy(() => import("./pages/Diagnose"));
const Knowledge = lazy(() => import("./pages/Knowledge"));
const Evaluation = lazy(() => import("./pages/Evaluation"));

const { Sider, Header, Content } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: <Link to="/">总览</Link> },
  {
    key: "/traces",
    icon: <ApartmentOutlined />,
    label: <Link to="/traces">Trace 浏览器</Link>,
  },
  { key: "/diagnose", icon: <RobotOutlined />, label: <Link to="/diagnose">AI 诊断</Link> },
  { key: "/knowledge", icon: <BookOutlined />, label: <Link to="/knowledge">知识库</Link> },
  { key: "/evaluation", icon: <ExperimentOutlined />, label: <Link to="/evaluation">评估</Link> },
];

export default function App() {
  const location = useLocation();
  const selected = location.pathname.startsWith("/traces")
    ? "/traces"
    : location.pathname;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth="0">
        <div style={{ color: "#fff", padding: 16, fontSize: 18, fontWeight: 600 }}>
          AgentTrace
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[selected]} items={menuItems} />
      </Sider>
      <Layout>
        <Header style={{ background: "#fff", padding: "0 24px" }}>
          <Typography.Title level={4} style={{ margin: 0, lineHeight: "64px" }}>
            AI Agent 自主诊断与优化平台
          </Typography.Title>
        </Header>
        <Content style={{ margin: 24 }}>
          <Suspense
            fallback={
              <div
                style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}
              >
                <Spin size="large" />
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/traces" element={<TraceExplorer />} />
              <Route path="/traces/:traceId" element={<TraceDetail />} />
              <Route path="/diagnose" element={<Diagnose />} />
              <Route path="/knowledge" element={<Knowledge />} />
              <Route path="/evaluation" element={<Evaluation />} />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
}
