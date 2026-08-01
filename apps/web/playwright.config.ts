import { defineConfig, devices } from "@playwright/test";

const WEB_PORT = 3100;
const API_PORT = 8100;

/**
 * e2e 用独立端口（3100/8100），避免与开发中的 make dev（3000/8000）抢占端口。
 * 后端固定使用 mock provider，因此 e2e 不需要任何 API Key，也不产生调用成本。
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,

  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "on-first-retry",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: [
    {
      command: `../api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: "../api",
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        APP_ENV: "test",
        LLM_PROVIDER: "mock",
        EMBEDDING_PROVIDER: "mock",
        CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT}`,
      },
    },
    {
      // 用 standalone 产物而非 dev server：测的是与生产镜像完全相同的产物，
      // 也避免 dev 模式的 HMR 干扰 hydration。static/public 的拷贝步骤与
      // apps/web/Dockerfile 保持一致。
      command: [
        "npm run build",
        "mkdir -p public",
        "rm -rf .next/standalone/.next/static .next/standalone/public",
        "cp -r .next/static .next/standalone/.next/static",
        "cp -r public .next/standalone/public",
        `PORT=${WEB_PORT} node .next/standalone/server.js`,
      ].join(" && "),
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${API_PORT}`,
      },
    },
  ],
});
