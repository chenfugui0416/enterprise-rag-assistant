# 任务表

> 规则：每项工作开始前先在此登记唯一编号、负责人、文件范围，状态置为 `IN_PROGRESS`；
> 完成后写明验证命令与真实结果，集成通过后才标 `DONE`。
> 状态取值：`TODO` / `IN_PROGRESS` / `BLOCKED` / `REVIEW` / `DONE`

## M0 · 工程骨架

| ID | 任务 | 负责人 | 文件范围 | 状态 | 验证 |
|---|---|---|---|---|---|
| M0-01 | 初始化 Git 仓库与忽略规则 | Claude | `.gitignore`, `LICENSE` | DONE | `git log --oneline` 有初始提交 |
| M0-02 | 后端最小 FastAPI 应用与配置层 | Claude | `apps/api/app/main.py`, `app/core/config.py` | DONE | `pytest` 13 passed |
| M0-03 | Provider 抽象 + Mock + OpenAI 兼容实现 | Claude | `apps/api/app/rag/providers/**` | DONE | `pytest` 11 项 provider 断言通过 |
| M0-04 | `/health` 端点与不泄露密钥的断言 | Claude | `apps/api/app/api/routes/health.py`, `tests/test_health.py` | DONE | `pytest tests/test_health.py` 2 passed |
| M0-05 | 前端 Next.js 16 + TS + Tailwind 骨架 | Claude | `apps/web/**` | DONE | `npm run build` 成功 |
| M0-06 | 首页展示后端健康状态（TanStack Query） | Claude | `apps/web/src/app/**`, `src/lib/api.ts` | DONE | `npm run lint && npm run typecheck` 通过 |
| M0-07 | 修复依赖漏洞（postcss / sharp） | Claude | `apps/web/package.json` | DONE | `npm audit` → 0 vulnerabilities |
| M0-08 | Playwright e2e 冒烟测试 | Claude | `apps/web/e2e/**`, `playwright.config.ts` | DONE | `npm run e2e` 2 passed |
| M0-09 | Docker Compose（Postgres+pgvector / Redis / api / web） | Claude | `docker-compose.yml`, `docker-compose.prod.yml`, `scripts/init-db.sql` | REVIEW | `docker compose config --quiet` 通过；镜像构建与实际启动待验证（见 M0-13） |
| M0-10 | 多阶段 Dockerfile（非 root 运行） | Claude | `apps/api/Dockerfile`, `apps/web/Dockerfile` | REVIEW | 语法已随 compose 校验；实际 build 待验证 |
| M0-11 | Makefile 六个入口命令 | Claude | `Makefile`, `scripts/dev.sh` | DONE | `make lint` / `make test` / `make e2e` 实跑通过 |
| M0-12 | GitHub Actions CI | Claude | `.github/workflows/ci.yml` | TODO | 需首次 push 后在 Actions 页面确认 |
| M0-13 | Docker 镜像构建 + pgvector 扩展验证 | Qizhou → Claude | 无（环境操作） | BLOCKED | Docker Desktop daemon 未就绪，需在本机 UI 完成启动/授权后重跑 `make up` |
| M0-14 | 协作文档（STATUS / TASKS / DECISIONS / SESSION_LOG / ARCHITECTURE） | Claude | `docs/**` | DONE | 文件已建立并填入真实验证结果 |
| M0-15 | 中文 README 与真实可执行命令 | Claude | `README.md` | DONE | 其中命令均已本机实跑 |
| M0-16 | 英文 README | Claude | `README_EN.md` | TODO | M5 前完成 |
| M0-17 | Codex 独立复核 M0 | Codex | 只读审阅 | BLOCKED | Codex API 端点持续 503，恢复后执行 |

## M1 · 最小 RAG 闭环（未开始）

| ID | 任务 | 负责人 | 文件范围 | 状态 | 验证 |
|---|---|---|---|---|---|
| M1-01 | SQLAlchemy 数据模型 + Alembic 迁移 | TODO | `apps/api/app/models/**`, `alembic/**` | TODO | 空库可执行迁移 |
| M1-02 | 文档解析（PDF/DOCX/MD/TXT） | TODO | `app/rag/loaders/**` | TODO | 单元测试 |
| M1-03 | 结构化切分策略 | TODO | `app/rag/chunking/**` | TODO | 单元测试 |
| M1-04 | 向量化与 pgvector 入库 | TODO | `app/rag/embeddings/**` | TODO | 集成测试 |
| M1-05 | Top-K 检索 | TODO | `app/rag/retrieval/**` | TODO | 集成测试 |
| M1-06 | 带引用的生成 | TODO | `app/rag/generation/**` | TODO | 10 道预设问题返回对应来源 |
| M1-07 | 低置信度拒答 | TODO | `app/rag/generation/**` | TODO | 无依据问题不编造 |
