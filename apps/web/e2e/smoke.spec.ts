import { expect, test } from "@playwright/test";

/**
 * 解析实验台的冒烟测试。
 *
 * 它同时覆盖 CORS 与 httpOnly Cookie 的携带——本地能跑、容器里却常出问题的一环。
 * 实验台位于受保护路由组内，因此每个用例都要先登录。
 */

const ADMIN_EMAIL = "e2e-admin@example.test";
const ADMIN_PASSWORD = "e2e-only-password-9f3a";

test.beforeEach(async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill(ADMIN_EMAIL);
  await page.getByLabel("密码").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/kb$/);
});

test("实验台可加载并展示后端健康状态", async ({ page }) => {
  await page.getByRole("link", { name: "解析实验台" }).click();

  await expect(page).toHaveURL(/\/lab$/);
  await expect(page.getByRole("heading", { name: "文档解析与结构化切分" })).toBeVisible();
  await expect(page.getByText("API 在线 · mock")).toBeVisible({ timeout: 15_000 });
});

test("上传 TXT 后展示解析块与 Chunk", async ({ page }) => {
  await page.goto("/lab");
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
