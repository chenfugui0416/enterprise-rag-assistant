"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { useCurrentUser, useLogin } from "@/lib/use-auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const loginMutation = useLogin();
  const { data: user } = useCurrentUser();

  // 已登录用户不该停在登录页
  useEffect(() => {
    if (user) router.replace("/kb");
  }, [user, router]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    loginMutation.mutate({ email: email.trim(), password });
  }

  const disabled = loginMutation.isPending || !email.trim() || !password;

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold tracking-tight">企业级 RAG 智能助手</h1>
        <p className="mt-1 text-sm text-slate-600">请使用企业邮箱登录</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700">
              邮箱
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700">
              密码
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
            />
          </div>

          {loginMutation.isError && (
            <p
              role="alert"
              data-testid="login-error"
              className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800"
            >
              {loginMutation.error.message}
            </p>
          )}

          <button
            type="submit"
            disabled={disabled}
            className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {loginMutation.isPending ? "登录中…" : "登录"}
          </button>
        </form>

        <p className="mt-6 text-xs text-slate-500">
          账号由管理员创建。首个管理员在服务启动时通过环境变量初始化。
        </p>
      </div>
    </div>
  );
}
