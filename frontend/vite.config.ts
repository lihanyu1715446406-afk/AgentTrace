import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发环境把 API 请求代理到后端（localhost:8000），避免跨域。
// 生产环境由 nginx 反向代理同路径（见 frontend/nginx.conf）。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://localhost:8000",
      "/overview": "http://localhost:8000",
      "/projects": "http://localhost:8000",
      "/traces": "http://localhost:8000",
      "/diagnose": "http://localhost:8000",
      "/knowledge": "http://localhost:8000",
      "/evaluation": "http://localhost:8000",
    },
  },
  build: {
    // 依赖分包：React 路由 / Ant Design / ECharts 拆成独立 chunk。
    // echarts 仅 Overview 页使用，配合路由懒加载做到按需加载。
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          antd: ["antd", "@ant-design/icons"],
          echarts: ["echarts", "echarts-for-react"],
        },
      },
    },
  },
});
