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
| M0-13 | pgvector + Redis 实际启动验证（VPS） | Claude | 无（环境操作） | DONE | VPS Ubuntu 24.04 上 `docker compose up -d db redis` 双 healthy；`\dx` 确认 vector 0.8.6 与 pg_trgm 1.6；HNSW 索引 + 余弦检索排序正确；Redis 读写正常、AOF 已开 |
| M0-13b | 本地 Docker Desktop 恢复 | Claude | 无（环境操作） | BLOCKED | 已修复两处根本损坏：ext4 超级块/设备尺寸不一致、containerd bbolt 元数据库损坏；但 Desktop 4.74.0 启动后仍反复自行关机，待重装或改用 colima |
| M0-14 | 协作文档（STATUS / TASKS / DECISIONS / SESSION_LOG / ARCHITECTURE） | Claude | `docs/**` | DONE | 文件已建立并填入真实验证结果 |
| M0-15 | 中文 README 与真实可执行命令 | Claude | `README.md` | DONE | 其中命令均已本机实跑 |
| M0-16 | 英文 README | Claude | `README_EN.md` | TODO | M5 前完成 |
| M0-17 | Codex 独立复核 M0 | Codex | 只读审阅 | BLOCKED | Codex API 端点持续 503，恢复后执行 |
| M0-18 | 修复备用开发端口的 CORS | Codex | `apps/api/app/core/config.py`, `.env.example`, `apps/api/tests/conftest.py`, `apps/api/tests/test_health.py` | DONE | `pytest tests/test_health.py` 6 passed；3001 预检 200；Playwright 页面显示 `status: ok` |

## M1 · 最小 RAG 闭环（已启动）

| ID | 任务 | 负责人 | 文件范围 | 状态 | 验证 |
|---|---|---|---|---|---|
| M1-01 | SQLAlchemy 数据模型 + Alembic 迁移 | Codex | `apps/api/app/models/**`, `apps/api/app/db/**`, `apps/api/alembic/**`, `apps/api/pyproject.toml` | DONE | `pytest` 16 passed；`alembic upgrade head` 已在真实 pgvector 库（VPS pg17 + vector 0.8.6，经 SSH 隧道）实际执行成功，版本 `0001_initial_schema (head)`；实测 6 张表、`document_chunks.embedding → vector(1024)`、3 个枚举均正确 |
| M1-02 | 文档解析（PDF/DOCX/MD/TXT） | Codex | `apps/api/app/rag/loaders/**`, `apps/api/tests/test_loaders.py`, `apps/api/pyproject.toml` | DONE | `pytest tests/test_loaders.py` 11 passed；全量 27 passed |
| M1-03 | 结构化切分策略 | Codex | `apps/api/app/rag/chunking/**`, `apps/api/tests/test_chunking.py`, `apps/api/pyproject.toml` | DONE | `pytest tests/test_chunking.py` 14 passed；全量 41 passed；ruff 通过 |
| M1-04 | 向量化与 pgvector 入库 | Codex | `apps/api/app/rag/embeddings/**`, `apps/api/app/models/**`, `apps/api/alembic/**`, `apps/api/tests/**` | DONE | `pytest tests/test_embeddings.py` 6 passed；真实 pgvector 集成测试 2 passed；全量 62 passed；迁移版本 `0002_document_chunks_hnsw_index (head)`；ruff 通过 |
| M1-04b | 修复 `error_message` 可能落入文档正文 | Claude | `apps/api/app/rag/embeddings/service.py`, `apps/api/tests/test_error_redaction.py` | DONE | 新增 `safe_error_detail()`：对 `SQLAlchemyError` 取 `exc.orig` 首行，结构性排除 `[SQL:]` 与 `[parameters:]`，不再靠长度截断碰运气。回归测试 5 passed，断言正文、SQL 段、参数段均不出现在结果中，且保留异常类型与原因 |
| M1-08 | 演示路由的生产环境隔离 | Claude | `apps/api/app/main.py`, `apps/api/tests/test_health.py` | DONE | `/demo/*` 与 `/documents/preview` 无任何认证与配额控制，可被任意调用触发文件上传、解析与模型调用。改为 `APP_ENV=production` 时不挂载，并加断言锁定（生产下请求返回 404，`/health` 仍 200）。M2 完成登录、权限与限流后再决定是否开放 |
| M1-05 | Top-K 检索 | Codex（实现）+ Claude（修复与测试） | `apps/api/app/rag/retrieval/**`, `apps/api/tests/test_retrieval_integration.py` | DONE | 真实 pgvector 集成测试 4 passed：余弦排序与分数精确匹配手工计算值、`ready` 状态过滤、阈值下推、`EXPLAIN` 确认走 `ix_document_chunks_embedding_hnsw`。全量 81 passed |
| M1-06 | 带引用的生成 | Codex（实现）+ Claude（修正与验收） | `apps/api/app/rag/generation/**`, `apps/api/scripts/run_m1_eval.py`, `data/eval/**` | BLOCKED | 机制已验收：11 题全链路跑通、0 失败、返回结构与引用元数据完整。**效果验收待真实 embedding**——mock 为语义无关的哈希向量，9 道有依据题的相似度均低于阈值而被拒答，标记为 limited 而非 pass。配置 `EMBEDDING_API_KEY` 后重跑 `scripts/run_m1_eval.py` 即得有效命中率 |
| M1-07 | 低置信度拒答 | Codex（实现）+ Claude（测试与验收） | `apps/api/app/rag/generation/**`, `apps/api/tests/test_generation.py` | REVIEW | 已验证：无依据问题 2/2 正确拒答、不产生引用、且完全不调用模型（防止其凭参数记忆编造企业事实）。**「有依据时不误拒」尚未验证**，需真实 embedding；阈值 0.35 为默认值，待 M4 校准 |

## M2 · 可使用的全栈产品（已启动）

| ID | 任务 | 负责人 | 文件范围 | 状态 | 验证 |
|---|---|---|---|---|---|
| M2-01a | 认证与权限（仅后端） | Codex | `apps/api/app/{api,core,schemas,services}/**`, `apps/api/tests/test_auth.py`, `.env.example`, `docs/{API,DECISIONS,SESSION_LOG}.md` | DONE | `ruff check .` 通过；`ruff format --check .` 74 files already formatted；全量 `pytest` 85 passed（真实 pgvector 可达，认证与既有数据库集成测试均实际执行）；迁移保持 `0002_document_chunks_hnsw_index (head)`；未修改 `apps/web/` 与既有演示路由 |
| M2-01b | 认证与权限（前端） | Claude | `apps/web/src/**`, `apps/web/e2e/**`, `apps/web/playwright.config.ts` | DONE | 统一 HTTP 层（`credentials: include`）、登录页、路由守卫、应用外壳与导航；实验台迁至 `/lab`，健康指示提升到顶栏；受保护路由用 Next 路由组隔离。**e2e 7 passed**，覆盖未登录跳转、登录、退出后会话失效、以及「密码错误」与「账号不存在」返回完全一致的提示 |
| M2-01c | CI 接入真实数据库 | Claude | `.github/workflows/ci.yml` | DONE | 认证引入后 e2e 必须有用户表，原 CI 必挂。api 与 e2e 两个 job 各挂 pgvector service，手工建扩展（service 容器不执行 init-db.sql）并执行迁移；前端依赖改用 `npm ci` 精确复现 |

## M2 Agent 层（进行中）

| 任务 | 产出 | 状态 | 验证 |
|---|---|---|---|
| M2-01 Provider 协议支持 tool calling | `app/rag/providers/base.py`（`ToolCall`/`ToolCallResult`/`complete_with_tools`）、`openai_compatible.py`、`mock.py` | DONE | `pytest tests/test_providers.py`；Mock 确定性脚本驱动循环 |
| M2-02 Agent 工具层 | `app/rag/agent/tools.py`（3 工具 + JSON Schema + 参数校验） | DONE | `pytest tests/test_agent_tools.py`（算术安全求值、错误回传、Schema 形状） |
| M2-03 Agent 编排循环 | `app/rag/agent/service.py`（检索分支、工具循环、步数上限拒答、寒暄短路） | DONE | `pytest tests/test_agent_service.py`（4 组断言） |
| M2-04 Agent API 端点 | `app/api/routes/` 新增 agent 问答端点 | TODO | 待真实模型 Key 后联调 |
| M2-05 前端思考链路可视化 | 前端展示每步工具调用与引用 | TODO | 依赖 M2-04 |

> 说明：M2-01~03 在 Mock Provider 下全链路可测（`pytest` 102 passed / 0 failed，`ruff` 全绿）。
> M2-04/05 需要真实模型 Key 才能端到端验证，故标记 TODO。

## M3 MimirQ 企业级中台集成（路线 B）

| 任务 | 产出 | 状态 | 验证 |
|---|---|---|---|
| M3-01 MimirQ 异步客户端与 JWT 缓存 | `app/rag/retrieval/mimirq_client.py`（登录、时效缓存、重试、检索代理、文档上传） | DONE | `pytest tests/test_mimirq_integration.py`（Token 复用与重试） |
| M3-02 检索协议适配层 | `app/rag/retrieval/mimirq_service.py`（`MimirQSearchService` 映射 `SearchResult`） | DONE | `pytest tests/test_mimirq_integration.py`（字段与评分完整映射） |
| M3-03 路由集成与热切换 | `apps/api/app/core/config.py`、`apps/api/app/api/routes/demo_rag.py` | DONE | `MIMIRQ_ENABLED` 开关支持热切换 |
| M3-04 架构决策与测试集 | `docs/DECISIONS.md` (ADR-0012)、`tests/test_mimirq_integration.py` | DONE | 全量 `pytest` 114 passed；`ruff check` 与 `format` 全绿 |


