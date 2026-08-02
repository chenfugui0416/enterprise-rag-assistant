import { expect, test } from "@playwright/test";

/**
 * 认证与路由守卫。
 *
 * 这些用例需要真实数据库：登录要查用户表，种子管理员由后端启动时创建。
 * playwright.config.ts 为后端注入了 SEED_ADMIN_* 环境变量。
 */

const ADMIN_EMAIL = "e2e-admin@example.test";
const ADMIN_PASSWORD = "e2e-only-password-9f3a";

test("未登录访问受保护页面会被送到登录页", async ({ page }) => {
  await page.goto("/kb");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "企业级 RAG 智能助手" })).toBeVisible();
});

test("根路径同样受保护", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/login$/);
});

test("密码错误时提示且不泄露账号是否存在", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill(ADMIN_EMAIL);
  await page.getByLabel("密码").fill("wrong-password");
  await page.getByRole("button", { name: "登录" }).click();

  const alert = page.getByRole("alert");
  await expect(alert).toBeVisible();
  await expect(alert).toHaveText("邮箱或密码错误");

  // 不存在的账号必须得到完全相同的提示
  await page.getByLabel("邮箱").fill("nobody-here@example.test");
  await page.getByLabel("密码").fill("wrong-password");
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page.getByRole("alert")).toHaveText("邮箱或密码错误");
});

test("登录后进入知识库页并显示当前用户与角色", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill(ADMIN_EMAIL);
  await page.getByLabel("密码").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录" }).click();

  await expect(page).toHaveURL(/\/kb$/);
  await expect(page.getByRole("heading", { name: "知识库" })).toBeVisible();
  await expect(page.getByText("管理员", { exact: true })).toBeVisible();
  await expect(page.getByText("API 在线 · mock")).toBeVisible({ timeout: 15_000 });
});

test("退出后会话失效，再访问受保护页会回到登录页", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("邮箱").fill(ADMIN_EMAIL);
  await page.getByLabel("密码").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/kb$/);

  await page.getByRole("button", { name: "退出" }).click();
  await expect(page).toHaveURL(/\/login$/);

  await page.goto("/kb");
  await expect(page).toHaveURL(/\/login$/);
});
