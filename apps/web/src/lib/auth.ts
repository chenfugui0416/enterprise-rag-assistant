/** 认证相关的类型与接口，字段名与后端 /auth/* 契约一致。 */

import { http } from "./http";

export type UserRole = "admin" | "member";

export interface AuthUser {
  id: string;
  email: string;
  /** 后端允许为空（管理员建号时可不填），展示前必须回退 */
  display_name: string | null;
  role: UserRole;
}

/** 没有显示名时退回邮箱前缀，避免界面出现空白或 "null"。 */
export function displayNameOf(user: AuthUser): string {
  return user.display_name?.trim() || user.email.split("@")[0];
}

export interface LoginResponse {
  user: AuthUser;
}

/** 登录成功后会话由 httpOnly Cookie 承载，响应体里没有 token。 */
export function login(email: string, password: string): Promise<LoginResponse> {
  return http.post<LoginResponse>(
    "/auth/login",
    { email, password },
    { fallbackMessage: "登录失败" },
  );
}

export function logout(): Promise<void> {
  return http.post<void>("/auth/logout", undefined, { fallbackMessage: "退出失败" });
}

/** 未登录时抛出 401 的 ApiError，由调用方决定跳转。 */
export function fetchCurrentUser(signal?: AbortSignal): Promise<AuthUser> {
  return http.get<AuthUser>("/auth/me", { signal, fallbackMessage: "获取登录状态失败" });
}

export function roleLabel(role: UserRole): string {
  return role === "admin" ? "管理员" : "成员";
}
