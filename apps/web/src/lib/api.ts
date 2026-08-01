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
