// 极简 fetch 封装：统一 API 基地址、错误处理与 JSON 解析。

// 同源部署时统一走 /api 前缀（Vite dev proxy / nginx 反向代理负责转发并去掉前缀），
// 这样 SPA 路由（/traces、/evaluation 等）与后端 API 不会互相抢路径。
// 前后端跨域部署时可设 VITE_API_BASE=http://<backend-host>:8000 直连后端。
const API_BASE: string = import.meta.env.VITE_API_BASE || "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(resp: Response): Promise<never> {
  let detail = resp.statusText;
  try {
    const text = await resp.text();
    if (text) detail = text;
  } catch {
    // 忽略响应体读取失败
  }
  throw new ApiError(resp.status, detail);
}

export async function apiGet<T>(
  path: string,
  headers?: Record<string, string>
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, { headers });
  if (!resp.ok) await parseError(resp);
  return (await resp.json()) as T;
}

export async function apiPost<T>(
  path: string,
  body: unknown,
  headers?: Record<string, string>
): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body),
  });
  if (!resp.ok) await parseError(resp);
  return (await resp.json()) as T;
}
