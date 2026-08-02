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

export interface QueryResponse {
  question: string;
  answer: string;
  refused: boolean;
  model_name: string;
  citations: Citation[];
  retrieved: Citation[];
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`后端返回 HTTP ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}

export async function previewDocument(
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

  const res = await fetch(`${API_BASE_URL}/documents/preview?${params}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `文档处理失败（HTTP ${res.status}）`);
  }
  return (await res.json()) as DocumentPreviewResponse;
}

export async function indexDemoDocument(file: File): Promise<IndexResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/demo/index`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `知识库写入失败（HTTP ${res.status}）`);
  }
  return (await res.json()) as IndexResponse;
}

export async function queryDemoKnowledgeBase(
  question: string,
  topK = 5,
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE_URL}/demo/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `问答请求失败（HTTP ${res.status}）`);
  }
  return (await res.json()) as QueryResponse;
}
