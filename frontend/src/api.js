/**
 * [INPUT]: 依赖浏览器 fetch、VITE_API_BASE_URL、VITE_DEMO_MODE 与 seller id
 * [OUTPUT]: 对外提供 createApiClient，统一 Closer API 请求、租户 token、GitHub Pages mock demo 与错误解析
 * [POS]: frontend/src 的 HTTP 边界，被 App.jsx 消费，隔离传输细节与界面状态
 * [PROTOCOL]: 变更时同步更新相关测试与公开文档
 */

import { createMockApiClient } from "./mockApi.js";

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE || "";

export function createApiClient({ baseUrl = DEFAULT_BASE_URL, sellerId }) {
  if (DEMO_MODE === "mock" || baseUrl === "mock") {
    return createMockApiClient({ sellerId });
  }

  const root = baseUrl.replace(/\/$/, "");

  async function request(path, options = {}) {
    const response = await fetch(`${root}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer seller:${sellerId}`,
        ...(options.headers || {}),
      },
    });
    const text = await response.text();
    const payload = text ? JSON.parse(text) : {};
    if (!response.ok) {
      const message = payload?.error?.message || payload?.message || `${response.status} ${response.statusText}`;
      throw new Error(message);
    }
    return payload;
  }

  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
    put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body || {}) }),
    patch: (path, body) => request(path, { method: "PATCH", body: JSON.stringify(body || {}) }),
  };
}
