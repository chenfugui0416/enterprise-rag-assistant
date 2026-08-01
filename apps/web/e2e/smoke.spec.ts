import { expect, test } from "@playwright/test";

/**
 * M0 冒烟测试：验证「前端渲染 + 跨域请求后端 + 后端返回健康状态」这条链路
 * 真实连通。它同时覆盖了 CORS 配置，这是本地能跑、容器里却常出问题的一环。
 */
test("首页可加载并展示后端健康状态", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "企业级 RAG 智能助手" })).toBeVisible();

  // 后端返回后，状态字段应显示 ok
  await expect(page.getByText("ok", { exact: true })).toBeVisible({ timeout: 15_000 });

  // M0 默认 mock provider，不应意外连到真实厂商（生成模型/向量模型两处均为 mock）
  await expect(page.getByText("mock", { exact: true })).toHaveCount(2);

  // 不应出现连接失败提示
  await expect(page.getByText("无法连接后端")).toHaveCount(0);
});

test("里程碑列表完整渲染", async ({ page }) => {
  await page.goto("/");
  for (const id of ["M0", "M1", "M2", "M3", "M4", "M5"]) {
    await expect(page.getByText(id, { exact: true })).toBeVisible();
  }
});
