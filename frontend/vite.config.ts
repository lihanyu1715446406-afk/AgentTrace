import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发环境把 /api 前缀的请求代理到后端（localhost:8000）并去掉前缀，避免跨域。
// 生产环境由 nginx 做同样的反向代理（见 frontend/nginx.conf）。
// 只代理 /api 可以避免与 SPA 路由（/traces、/evaluation 等）冲突。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
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
