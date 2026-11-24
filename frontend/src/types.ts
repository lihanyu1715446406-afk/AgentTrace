// 与后端 REST API 返回结构一一对应的类型定义。
// 依据：backend/app/schemas/ 与 backend/app/api/routes/。

export interface CostByModel {
  model_name: string;
  total_tokens: number;
  estimated_cost: number | null;
}

export interface RecentTrace {
  trace_id: string;
  name: string;
  status: string;
  started_at: string;
  duration_ms: number | null;
}

export interface Overview {
  total_traces: number;
  failed_traces: number;
  total_spans: number;
  total_projects: number;
  total_tokens: number;
  total_cost: number | null;
  cost_by_model: CostByModel[];
  recent_traces: RecentTrace[];
}

export interface ProjectRead {
  project_id: string;
  name: string;
}

export interface TraceSummary {
  trace_id: string;
  project_id: string;
  name: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  metadata: Record<string, unknown> | null;
}

export interface SpanDetail {
  span_id: string;
  trace_id: string;
  parent_span_id: string | null;
  name: string;
  span_type: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  input: unknown;
  output: unknown;
  error: unknown;
}

export interface TokenUsage {
  model_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number | null;
  currency: string;
}

export interface ModelCost {
  model_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number | null;
}

export interface CostSummary {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost: number | null;
  by_model: ModelCost[];
}

export interface TraceDetailResponse {
  trace: TraceSummary;
  spans: SpanDetail[];
  token_usages: TokenUsage[];
  cost: CostSummary;
}

export interface AnalysisResult {
  role: string;
  summary: string;
  findings: string[];
  data: Record<string, unknown>;
  error: string | null;
}

export interface SupervisorResult {
  query: string;
  task_type: string | null;
  assigned_roles: string[];
  analysis_results: AnalysisResult[];
  final_report: string;
}

export interface KnowledgeDocumentRead {
  document_id: string;
  title: string;
  source: string;
  document_type: string;
  created_at: string;
}

export interface EvalSample {
  sample_id: string;
  query: string;
  expected_task_type: string | null;
  expected_tool_names: string[];
  expected_facts: string[];
  golden_answer: string | null;
}

export interface EvaluationDataset {
  dataset_name: string;
  metrics: Record<string, string>;
  samples: EvalSample[];
}
