import { AppShell } from "@/components/app-shell";
import { AuthGuard } from "@/components/auth-guard";

/**
 * 受保护路由组的布局：先确认登录状态，再渲染应用外壳。
 * 登录页不在本组内，因此不会被守卫拦截。
 */
export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
