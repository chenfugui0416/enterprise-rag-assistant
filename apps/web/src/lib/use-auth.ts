"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type AuthUser, fetchCurrentUser, login, logout } from "./auth";
import { ApiError } from "./http";

export const AUTH_QUERY_KEY = ["auth", "me"] as const;

/**
 * 当前登录用户。未登录时 query 进入 error 态（401），而不是抛到界面上，
 * 由 AuthGuard 决定跳转。
 */
export function useCurrentUser() {
  return useQuery<AuthUser, ApiError>({
    queryKey: AUTH_QUERY_KEY,
    queryFn: ({ signal }) => fetchCurrentUser(signal),
    // 401 属于正常的"未登录"，重试没有意义
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: (data) => {
      // 直接写入缓存，省掉一次 /auth/me 往返
      queryClient.setQueryData(AUTH_QUERY_KEY, data.user);
      router.replace("/kb");
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      // 无论后端是否成功清 Cookie，本地都必须丢弃全部缓存：
      // 残留的知识库、文档、会话数据不应被下一个登录者看到
      queryClient.clear();
      router.replace("/login");
    },
  });
}
