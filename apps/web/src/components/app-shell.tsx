"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/lib/api";
import { displayNameOf, roleLabel } from "@/lib/auth";
import { useCurrentUser, useLogout } from "@/lib/use-auth";

const NAV_ITEMS = [
  { href: "/kb", label: "知识库" },
  { href: "/chat", label: "问答" },
  { href: "/lab", label: "解析实验台" },
];

/** 登录后的应用外壳：顶部导航 + 当前用户 + 退出。 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const logoutMutation = useLogout();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    retry: 1,
    refetchInterval: 60_000,
  });

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-6 px-6">
          <Link href="/kb" className="text-sm font-semibold tracking-tight">
            企业级 RAG 智能助手
          </Link>

          <nav className="flex items-center gap-1">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-md px-3 py-1.5 text-sm transition ${
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden items-center gap-1.5 text-xs sm:flex">
              {health.isPending && <span className="text-slate-500">API 检测中</span>}
              {health.isError && <span className="font-medium text-red-700">API 离线</span>}
              {health.isSuccess && (
                <>
                  <span className="size-2 rounded-full bg-emerald-500" />
                  <span className="text-slate-500">
                    API 在线 · {health.data.embedding_provider}
                  </span>
                </>
              )}
            </span>
            {user && (
              <span className="text-slate-600">
                {displayNameOf(user)}
                <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                  {roleLabel(user.role)}
                </span>
              </span>
            )}
            <button
              type="button"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-50"
            >
              {logoutMutation.isPending ? "退出中…" : "退出"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
    </div>
  );
}
