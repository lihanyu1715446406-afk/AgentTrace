// 访问 /traces 所需的项目标识与 API Key（存浏览器 localStorage）。
// 后端鉴权：X-API-Key 头 + project_id 查询参数必须匹配同一项目。

const API_KEY = "agenttrace_api_key";
const PROJECT_ID = "agenttrace_project_id";

export function getApiKey(): string {
  return localStorage.getItem(API_KEY) ?? "";
}

export function setApiKey(key: string): void {
  localStorage.setItem(API_KEY, key);
}

export function getProjectId(): string {
  return localStorage.getItem(PROJECT_ID) ?? "";
}

export function setProjectId(id: string): void {
  localStorage.setItem(PROJECT_ID, id);
}
