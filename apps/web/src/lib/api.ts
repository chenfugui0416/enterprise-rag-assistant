import { http } from "./http";

/** 后端 /health 的响应结构，与 apps/api/app/api/routes/health.py 保持一致。 */
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  env: string;
  llm_provider: string;
  embedding_provider: string;
  embedding_dim: number;
}

export type ParsedBlockKind = "page" | "heading" | "paragraph" | "table" | "code" | "text";

export interface ParsedBlock {
  index: number;
  kind: ParsedBlockKind;
  text: string;
  page_number: number | null;
  section_title: string | null;
}

export interface DocumentChunk {
  index: number;
  text: string;
  token_count: number;
  page_number: number | null;
  section_title: string | null;
  source_block_indices: number[];
}

export interface DocumentPreviewResponse {
  filename: string;
  media_type: string;
  size_bytes: number;
  page_count: number | null;
  encoding: string | null;
  character_count: number;
  block_count: number;
  chunk_count: number;
  total_tokens: number;
  config: {
    max_tokens: number;
    chunk_overlap: number;
  };
  blocks: ParsedBlock[];
  chunks: DocumentChunk[];
}

export interface IndexResponse {
  document_id: string;
  filename: string;
  status: string;
  chunk_count: number;
  embedding_model: string;
  duplicate: boolean;
}

export interface Citation {
  document_id: string;
  document_name: string;
  chunk_index: number;
  score: number;
  page_number: number | null;
  section_title: string | null;
  content: string;
}

export interface ExecutionTrace {
  trace_id: string;
  total_duration_ms: number;
  retrieval_mode: string;
  retrieval_duration_ms: number;
  retrieved_count: number;
  top_score: number | null;
  llm_duration_ms: number;
  refused: boolean;
}

export interface AgentStep {
  index: number;
  tool_name: string;
  arguments: string;
  result: string;
}

export interface QueryResponse {
  question: string;
  answer: string;
  refused: boolean;
  model_name: string;
  citations: Citation[];
  retrieved: Citation[];
  execution_trace?: ExecutionTrace | null;
  agent_steps?: AgentStep[] | null;
}

export { API_BASE_URL } from "./http";

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return http.get<HealthResponse>("/health", { signal, fallbackMessage: "健康检查失败" });
}

export function previewDocument(
  file: File,
  maxTokens: number,
  chunkOverlap: number,
): Promise<DocumentPreviewResponse> {
  const params = new URLSearchParams({
    max_tokens: String(maxTokens),
    chunk_overlap: String(chunkOverlap),
  });
  const form = new FormData();
  form.append("file", file);
  return http.postForm<DocumentPreviewResponse>(`/documents/preview?${params}`, form, {
    fallbackMessage: "文档处理失败",
  });
}

export function indexDemoDocument(file: File): Promise<IndexResponse> {
  const form = new FormData();
  form.append("file", file);
  return http.postForm<IndexResponse>("/demo/index", form, {
    fallbackMessage: "知识库写入失败",
  });
}

export function queryDemoKnowledgeBase(
  question: string,
  topK = 5,
  useAgent = false,
): Promise<QueryResponse> {
  return http.post<QueryResponse>(
    "/demo/query",
    { question, top_k: topK, use_agent: useAgent },
    { fallbackMessage: "问答请求失败" },
  );
}
