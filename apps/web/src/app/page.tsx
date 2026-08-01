"use client";

import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL, fetchHealth } from "@/lib/api";

const MILESTONES = [
  { id: "M0", title: "工程骨架", detail: "FastAPI + Next.js + Postgres/pgvector + Redis + CI" },
  { id: "M1", title: "最小 RAG 闭环", detail: "解析、切分、向量化、检索、带引用生成" },
  { id: "M2", title: "全栈产品", detail: "登录、知识库管理、流式问答、引用预览" },
  { id: "M3", title: "企业级可靠性", detail: "多租户隔离、审计日志、限流、注入防护" },
  { id: "M4", title: "评测", detail: "≥30 题评测集、命中率、拒答表现、延迟" },
  { id: "M5", title: "部署与证据", detail: "VPS 部署、架构图、演示与可验证指标" },
];

export default function Home() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
  });

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">企业级 RAG 智能助手</h1>
      <p className="mt-2 text-sm text-slate-600">
        带引用、权限隔离与离线评测的企业知识库问答系统。当前处于 M0 工程骨架阶段。
      </p>

      <section className="mt-10 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">后端连通性</h2>
          <button
            type="button"
            onClick={() => void health.refetch()}
            disabled={health.isFetching}
            className="rounded-md border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
          >
            重新检测
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-500">目标地址：{API_BASE_URL}/health</p>

        <div className="mt-4">
          {health.isPending && <p className="text-sm text-slate-500">检测中…</p>}

          {health.isError && (
            <div className="rounded-md bg-red-50 p-4 text-sm text-red-800">
              <p className="font-medium">
                无法连接后端：
                {health.error instanceof Error ? health.error.message : "未知错误"}
              </p>
              <p className="mt-1 text-red-700">
                请确认后端已启动（<code className="font-mono">make dev</code>），且{" "}
                <code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code> 指向正确地址。
              </p>
            </div>
          )}

          {health.isSuccess && (
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-3">
              <Field label="状态" value={health.data.status} highlight />
              <Field label="环境" value={health.data.env} />
              <Field label="版本" value={health.data.version} />
              <Field label="生成模型" value={health.data.llm_provider} />
              <Field label="向量模型" value={health.data.embedding_provider} />
              <Field label="向量维度" value={String(health.data.embedding_dim)} />
            </dl>
          )}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-medium">里程碑</h2>
        <ol className="mt-3 space-y-2">
          {MILESTONES.map((m) => (
            <li
              key={m.id}
              className="flex gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm"
            >
              <span className="font-mono font-medium text-slate-400">{m.id}</span>
              <span>
                <span className="font-medium">{m.title}</span>
                <span className="ml-2 text-slate-500">{m.detail}</span>
              </span>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function Field({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd
        className={`mt-0.5 font-mono ${
          highlight ? "font-semibold text-emerald-600" : "text-slate-800"
        }`}
      >
        {value}
      </dd>
    </div>
  );
}
