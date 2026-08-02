import { expect, test } from "@playwright/test";

/**
 * M0 冒烟测试：验证「前端渲染 + 跨域请求后端 + 后端返回健康状态」这条链路
 * 真实连通。它同时覆盖了 CORS 配置，这是本地能跑、容器里却常出问题的一环。
 */
test("文档实验台可加载并展示后端健康状态", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "企业知识库 RAG 助手" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "文档解析与结构化切分" })).toBeVisible();

  await expect(page.getByText("API 在线 · mock", { exact: true })).toBeVisible({ timeout: 15_000 });

  // 不应出现连接失败提示
  await expect(page.getByText("无法连接后端")).toHaveCount(0);
});

test("上传 TXT 后展示解析块与 Chunk", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("选择文档").setInputFiles({
    name: "员工手册.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("第一章 年假制度\n\n员工每年享有十天年假。", "utf-8"),
  });
  await page.getByRole("button", { name: "解析并切分" }).click();

  await expect(page.getByText("员工手册.txt", { exact: true })).toBeVisible();
  await expect(page.getByText("CHUNK 0", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: /解析块/ }).click();
  await expect(page.getByText("BLOCK 0", { exact: true })).toBeVisible();
});
