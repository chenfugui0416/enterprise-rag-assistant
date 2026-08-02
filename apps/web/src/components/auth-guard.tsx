"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useCurrentUser } from "@/lib/use-auth";

/**
 * 路由保护：未登录时跳转到登录页。
 *
 * 这只是体验层的守卫，不是安全边界——真正的鉴权必须由后端在每个接口上执行。
 * 前端能做的只是别把空壳页面显示给未登录用户。
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isPending, isError, error } = useCurrentUser();

  useEffect(() => {
    if (isError && error?.isUnauthorized) {
      router.replace("/login");
    }
  }, [isError, error, router]);

  if (isPending) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-sm text-slate-500">正在确认登录状态…</p>
      </div>
    );
  }

  if (isError) {
    // 401 时上面的 effect 已在跳转，这里只处理"后端挂了"这类错误
    if (error?.isUnauthorized) return null;
    return (
      <div className="mx-auto mt-16 max-w-md rounded-lg bg-red-50 p-6 text-sm text-red-800">
        <p className="font-medium">无法确认登录状态</p>
        <p className="mt-1 text-red-700">{error?.message}</p>
      </div>
    );
  }

  if (!user) return null;
  return <>{children}</>;
}
