# 会话记录

> 每个工作会话结束前追加一条。格式见「项目交接文档.md」。

---

## 2026-08-01 — Claude（代 Codex 执行 M0）

- **任务**：M0-01 ~ M0-15

- **背景说明（重要）**：
  按交接文档分工，M0 应由 Codex 执行、Claude 审阅。本次派发 Codex 时，其上游 API 端点
  持续返回 `503 Service Unavailable`（重连 5 次后失败，进程退出码为 0 但零产出）。
  为不阻塞项目进度，改由 Claude 直接执行 M0，Codex 的独立复核（M0-17）挂起，待其恢复
  后补做。此处如实记录，避免日后误以为 M0 经过双方交叉验证。

- **完成**：
  - 目录由「企业级 RAG 助手」重命名为 `enterprise-rag-assistant`（ADR-0003）
  - 后端：FastAPI + pydantic-settings 配置层 + `/health`
  - Provider 抽象层：Protocol 定义、Mock 实现、OpenAI 兼容实现、工厂装配（ADR-0001）
  - 后端测试 13 项，含「健康检查不泄露密钥」与「缺 Key 时装配阶段即失败」两条安全断言
  - 前端：Next.js 16 + React 19 + TS + Tailwind 4，首页展示后端连通性与里程碑
  - 前端服务端状态改用 TanStack Query（ADR-0004）
  - 修复 postcss / sharp 传递依赖漏洞（用 overrides，未降级 Next）
  - Playwright e2e 2 项，针对 standalone 生产产物运行（ADR-0005）
  - 多阶段 Dockerfile（后端与前端均以非 root 用户运行）
  - `docker-compose.yml` + `docker-compose.prod.yml` + `scripts/init-db.sql`
  - `Makefile` 六个入口命令 + `scripts/dev.sh`
  - GitHub Actions CI：api / web / e2e / docker 四个 job
  - 文档：README、ARCHITECTURE、STATUS、TASKS、DECISIONS、SESSION_LOG

- **修改文件**：见首次提交的文件清单（`git show --stat HEAD`）

- **运行命令与真实结果**：
  ```
  cd apps/api && .venv/bin/python -m pytest        → 13 passed
  cd apps/api && .venv/bin/ruff check .            → All checks passed!
  cd apps/api && .venv/bin/ruff format --check .   → 25 files already formatted
  cd apps/web && npm run lint                      → 0 problems
  cd apps/web && npm run typecheck                 → 通过
  cd apps/web && npm run build                     → 成功
  cd apps/web && npm audit                         → found 0 vulnerabilities
  cd apps/web && npm run e2e                       → 2 passed
  docker compose config --quiet                    → 通过
  docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet → 通过
  ```

- **过程中被测试真实抓到的问题**（保留记录，这些是项目的工程证据）：
  1. `ruff` 报 SIM117：`openai_compatible.py` 中嵌套 `with` → 合并为单条 `async with`。
  2. React 19 的 `react-hooks/set-state-in-effect` 拒绝 effect 内同步 setState；
     绕过写法仍被静态分析判定为违规 → 引入 TanStack Query（ADR-0004）。
  3. e2e 首次失败：页面停在「检测中…」，`/health` 请求根本未发出。加 console/network
     监听后定位为 dev server 的 HMR WebSocket 握手失败导致未 hydrate → 改用 standalone
     产物（ADR-0005）。
  4. `next start` 与 `output: standalone` 不兼容（Next 明确警告）→ e2e 改为按 Dockerfile
     同样的方式拷贝 `.next/static` 与 `public` 后运行 `node .next/standalone/server.js`。
  5. `npm audit` 报 3 个 high（postcss / sharp），而 `npm audit fix --force` 会把 Next
     降级到 9.x → 改用 `overrides` 提升传递依赖版本，构建与 e2e 复验通过后保留。
  6. `docker compose config` 因 `env_file: .env` 缺失而失败 → 改为
     `path: .env` + `required: false`，保证无 `.env` 的环境（CI）也能解析。

- **已知问题**：见 `docs/STATUS.md`「已知问题」。核心是 Docker daemon 未就绪，
  镜像构建与 pgvector 实际可用性尚未验证。

- **下一位执行者**：Qizhou（解除 Docker 阻塞）→ Codex（M0-17 复核）→ M1

- **建议下一步**：
  1. 在本机启动 Docker Desktop，执行 `make up` 并确认 `\dx` 中存在 `vector` 与 `pg_trgm`。
  2. 创建 GitHub 仓库并首次 push，确认 CI 全绿。
  3. 取得模型 API Key 写入本地 `.env`。
  4. 开始 M1-01 数据模型与迁移。
