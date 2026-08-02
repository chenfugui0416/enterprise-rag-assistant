/**
 * 统一的 HTTP 客户端。
 *
 * 所有请求都带 credentials: "include"——会话走 httpOnly Cookie，
 * JS 读不到也就无法被 XSS 窃取，代价是必须显式携带凭据。
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** 401 表示会话失效，调用方据此跳登录页而不是弹错误 */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isForbidden(): boolean {
    return this.status === 403;
  }
}

async function toError(res: Response, fallback: string): Promise<ApiError> {
  // 后端错误统一放在 detail 字段；解析失败时退回通用文案，
  // 不把原始响应体直接抛给用户，避免泄露内部信息
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
  const detail = typeof body?.detail === "string" ? body.detail : null;
  return new ApiError(res.status, detail ?? `${fallback}（HTTP ${res.status}）`);
}

interface RequestOptions {
  signal?: AbortSignal;
  fallbackMessage?: string;
}

async function request<T>(
  path: string,
  init: RequestInit,
  { signal, fallbackMessage = "请求失败" }: RequestOptions = {},
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal,
      credentials: "include",
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "无法连接服务器，请确认后端已启动。");
  }

  if (!res.ok) throw await toError(res, fallbackMessage);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const http = {
  get<T>(path: string, options?: RequestOptions) {
    return request<T>(path, { method: "GET" }, options);
  },

  post<T>(path: string, body?: unknown, options?: RequestOptions) {
    return request<T>(
      path,
      {
        method: "POST",
        headers: body === undefined ? undefined : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      },
      options,
    );
  },

  /** 上传走 FormData，不能手动设 Content-Type，否则 boundary 会丢 */
  postForm<T>(path: string, form: FormData, options?: RequestOptions) {
    return request<T>(path, { method: "POST", body: form }, options);
  },

  delete<T>(path: string, options?: RequestOptions) {
    return request<T>(path, { method: "DELETE" }, options);
  },
};
