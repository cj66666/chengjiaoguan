/**
 * [INPUT]: 依赖 Vite、@vitejs/plugin-react 与环境变量 VITE_API_PROXY_TARGET、VITE_BASE_PATH
 * [OUTPUT]: 对外提供 Vite React 构建配置、本地 /api 代理与 GitHub Pages base path
 * [POS]: frontend 的开发服务器边界，避免浏览器 CORS 干扰本地 FastAPI 联调
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";
const base = process.env.VITE_BASE_PATH || "/";

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
