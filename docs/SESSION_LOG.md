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

## 2026-08-01 — Codex（完成 M1-01）

- **任务**：M1-01 SQLAlchemy 数据模型 + Alembic 迁移
- **完成**：
  - 加入 SQLAlchemy 2、Alembic、psycopg、pgvector 和 greenlet 依赖。
  - 建立用户、知识库、文档、文档切片、会话、消息六张核心表的模型。
  - 文档切片预留 `VECTOR(1024)`，枚举状态和级联删除策略写入模型与迁移。
  - 建立异步数据库会话入口和可读取项目配置的 Alembic 环境。
  - 初始迁移创建 `pgcrypto`、`vector`、`pg_trgm` 扩展，并可离线生成完整 SQL。
  - 增加模型元数据、向量维度和枚举稳定性测试。
- **修改文件**：`apps/api/pyproject.toml`、`apps/api/app/db/**`、`apps/api/app/models/**`、
  `apps/api/tests/test_models.py`、`apps/api/alembic.ini`、`apps/api/alembic/**`，以及项目状态文档。
- **运行命令与真实结果**：
  - `cd apps/api && uv pip install -e '.[dev]'` → 依赖安装成功。
  - `cd apps/api && .venv/bin/python -m pytest` → **16 passed**。
  - `cd apps/api && .venv/bin/ruff check .` → **All checks passed**。
  - `cd apps/api && .venv/bin/ruff format --check .` → **36 files already formatted**。
  - `cd apps/api && .venv/bin/alembic upgrade head --sql` → 生成 3 个枚举、6 张表和 `VECTOR(1024)`。
- **已知问题**：真实 `alembic upgrade head` 尚未完成。当前本机 PostgreSQL 没有 `vector` 扩展，
  Docker Desktop daemon 也未启动；待 `pgvector/pgvector:pg17` 可用后重跑。
- **下一位执行者**：Claude 审阅模型关系、迁移约束和向量维度；随后 Codex 开始 M1-02 文档解析。

## 2026-08-01 — Codex（完成 M1-02）

- **任务**：M1-02 PDF、DOCX、Markdown、TXT 文档解析
- **完成**：
  - 定义格式无关的 `ParsedDocument` 与 `ParsedBlock`，为 M1-03 提供页码、标题、块类型等元数据。
  - PDF 按页提取文本并保留一基页码；加密、损坏和无文本 PDF 返回统一解析错误。
  - DOCX 按文档顺序提取标题、段落和表格，并把当前标题附到后续内容块。
  - Markdown 通过 CommonMark Token 解析可见正文、列表、标题与代码块，不采用正则剥标签。
  - TXT 优先 UTF-8，随后支持 GB18030、Big5，并以通用编码探测作为回退。
  - 统一检查文件存在性、50 MiB 默认限制、空内容、二进制伪装和不支持的扩展名。
  - 公共错误信息不携带源文件绝对路径。
- **修改文件**：`apps/api/app/rag/loaders/**`、`apps/api/tests/test_loaders.py`、
  `apps/api/pyproject.toml`、README 与项目状态文档。
- **运行命令与真实结果**：
  - `cd apps/api && uv pip install -e '.[dev]'` → 解析依赖安装成功。
  - `cd apps/api && .venv/bin/python -m pytest tests/test_loaders.py` → **11 passed**。
  - `cd apps/api && .venv/bin/python -m pytest` → **27 passed**。
  - `cd apps/api && .venv/bin/ruff check .` → **All checks passed**。
  - `cd apps/api && .venv/bin/ruff format --check .` → **45 files already formatted**。
- **测试中修正的问题**：
  1. 短中文 GB18030 被通用探测器误判为 CP949；改为 UTF-8 优先、中文编码优先、通用回退。
  2. 损坏 DOCX 初次暴露底层 `BadZipFile`；增加异常封装并补回归测试。
- **已知边界**：尚无扫描 PDF OCR、旧版 `.doc`、复杂 DOCX 浮动对象或加密 PDF 解密。
- **下一位执行者**：Claude 审阅解析结果契约；随后 Codex 执行 M1-03 结构化切分。

## 2026-08-01 — Codex（完成 M1-03）

- **任务**：根据页码、标题、段落和 Token 长度实现结构化切分。
- **完成**：
  - 新增 `app.rag.chunking` 公共 API、`ChunkingConfig`、不可变 `Chunk` 和可注入 `Tokenizer` 协议。
  - 默认使用 `tiktoken` `cl100k_base`；支持 `max_tokens`、`chunk_overlap`、`min_chunk_tokens` 和编码名称配置。
  - 先按页码/标题建立硬边界，再在同一上下文内按段落拼接；长段优先按句/行组织，最后用 Token 窗口保证上限。
  - 切片保留稳定索引、实际 Token 数、页码、标题和来源 block 索引，可直接接收 M1-02 的 `ParsedDocument`。
  - 空块会跳过，空文档返回空元组；参数校验拒绝非正上限、非法 overlap 和不合理最小长度。
- **修改文件**：`apps/api/app/rag/chunking/**`、`apps/api/tests/test_chunking.py`、
  `apps/api/pyproject.toml`，以及 README、STATUS、TASKS、ARCHITECTURE 和本日志。
- **运行命令与真实结果**：
  - `cd apps/api && uv pip install -e '.[dev]'` → 安装 `tiktoken==0.13.0` 成功。
  - `cd apps/api && .venv/bin/python -m pytest tests/test_chunking.py` → **14 passed**。
  - `cd apps/api && .venv/bin/python -m pytest` → **41 passed**。
  - `cd apps/api && .venv/bin/ruff check .` → **All checks passed**。
  - `cd apps/api && .venv/bin/ruff format --check .` → 结果见 `docs/STATUS.md`，全部文件已格式化。
- **已知边界**：尚未接入 Embedding、pgvector、上传接口或检索服务；页码/标题边界和 Token overlap
  已在单元测试覆盖，真实数据库环境仍受 Docker/pgvector 阻塞影响。
- **下一位执行者**：Claude 审阅切分策略和来源元数据；随后 Codex 执行 M1-04 向量化与 pgvector 入库。

## 2026-08-02 — Codex（修复本地 3001 端口 CORS）

- **任务**：修复前端运行在 `http://localhost:3001` 时健康检查显示 `Failed to fetch`。
- **原因**：后端正常返回 `/health`，但默认 CORS 仅允许 `http://localhost:3000`，导致 3001
  来源的浏览器预检返回 `400 Disallowed CORS origin`。
- **完成**：开发默认来源和 `.env.example` 同时允许 localhost/127.0.0.1 的 3000、3001；
  新增四个来源的参数化预检测试。
- **验证**：`pytest tests/test_health.py` → **6 passed**；3001 OPTIONS 请求 → **HTTP 200**；
  Playwright 加载 `http://localhost:3001` 后 `/health` → **200**，页面显示 `status: ok`。

---

## 2026-08-01（第二段） — Claude：Docker 环境抢修 + M0-13 验证

- **任务**：M0-13（pgvector 实际启动验证）、M0-13b（本地 Docker 恢复）

- **背景**：本机 Docker daemon 持续返回 HTTP 500，`make up` 无法执行，M0-13 被阻塞。

- **根因诊断（两处独立损坏）**：

  1. **ext4 超级块与设备尺寸不一致**
     `e2fsck` 报 `error code 8`：superblock 记录 122,060,800 blocks，设备实际只有
     120,686,336 blocks（差 5,368 MiB）。原因是虚拟磁盘曾从 476,800 MiB 被调小到
     471,432 MiB，`Docker.raw` 被截断而超级块未同步。宿主机 `/System/Volumes/Data`
     已用 93%（仅剩 31 GB）是诱因。
     **修复**：`Docker.raw` 是稀疏文件，把 apparent size 补回 `122060800 × 4096 + 1 MiB`
     不占用实际磁盘空间（实占仍为 12.66 GiB），并把 `DiskSizeMiB` 显式锁定为 476801
     防止再次截断。此后 `e2fsck` 能完整跑完 Pass 1–5，错误码由 8 降为 4。

  2. **containerd 的 bbolt 元数据库损坏**
     `panic: assertion failed: Page expected to be: 1098, but self identifies as 0`
     出现在 `bbolt.(*DB).loadFreelist`，containerd 每次启动即 panic，dockerd 无法拉起。
     panic 堆栈中 bbolt 路径长度 `0x49`（73 字符）恰好等于
     `/var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db`。
     **尝试修复**：`bbolt surgery freelist abandon` 与 `clear-page` 均失败——page 1098
     整页被清零（自称 id=0），属实际数据页丢失，不可恢复。
     **处置**：备份该 8 MB 文件后删除，由 containerd 重建。卷数据（含
     `hermes-webio-check_hermes-data`）位于 `/var/lib/docker/volumes`，未受影响。

- **使用工具**：`brew install e2fsprogs`（1.47.4）+ `hdiutil attach -nomount` 把
  `Docker.raw` 挂成块设备（属主为当前用户，无需 sudo）；`debugfs` 定位并清理孤立
  inode；`go install go.etcd.io/bbolt/cmd/bbolt` 诊断 bbolt。

- **e2fsck 收敛过程**：两个 `/lost+found` 下的空目录 inode（344081、344731）的 `..`
  指向 NULL inode，e2fsck 每轮都把它们重新挂回 lost+found 再报修不了，形成死循环。
  `unlink` + `kill_file` + `freei` 均无效，最终用 `debugfs clri` 将 inode 结构整体清零
  才收敛。最终 `Filesystem state: clean`。

- **结果**：
  - 磁盘层面完全修复：`e2fsck` 五个 Pass 零错误，后续启动磁盘错误计数为 0。
  - containerd panic 消除：删除 meta.db 后两次启动均正常 `serving...`。
  - **但 Docker Desktop 4.74.0 应用层仍反复自行关机**（`recovering from engine crash:
    context canceled`），本地 daemon 最终未能起来。判断为 Desktop 自身问题，
    建议重装或改用 colima（本机已有 colima context）。

- **改走 VPS 完成 M0-13**（Ubuntu 24.04 / Docker 29.1.3 / Compose 2.37.1）：
  ```
  rsync 项目 → cp .env.example .env（端口改 55432/56379 避开既有服务）
  docker compose config --quiet          → 通过
  docker compose up -d db redis          → rag-db / rag-redis 双 healthy（20 秒内）
  \dx                                    → vector 0.8.6、pg_trgm 1.6、PostgreSQL 17.10
  HNSW 索引 + 余弦检索                    → 年假制度 1.0000 > 年假申请 0.9939 > 报销流程 0.0000
  redis-cli set/get/del + appendonly      → 读写正常，AOF 已开启
  docker stats                           → rag-db 74.3 MiB、rag-redis 12.1 MiB
  ```
  这证明 `docker-compose.yml` 与 `scripts/init-db.sql` 在真实 Linux 环境下可用，
  且 pgvector 不只是"装上了"，而是真能建 HNSW 索引并返回正确的相似度排序。

- **VPS 现状备注**：1 核 / 961 MiB 内存（可用约 226 MiB）+ 1 GiB swap，23 GB 磁盘（剩 11 GB），
  已运行 7 个生产容器，80/443 端口被占用。M5 若在此部署需先规划反向代理与内存预算；
  另发现 `fwupd` 常驻占用约 195 MB，服务器场景可考虑关闭。

- **已知问题**：本地 Docker Desktop 未恢复（见 `docs/STATUS.md` 已知问题 1）。

- **建议下一步**：重装 Docker Desktop 或启用 colima 以恢复本地容器能力；
  M5 部署前先解决 VPS 的内存与端口规划。

---

## 2026-08-02 — Codex（完成 M1-04）

- **任务**：批量向量化、pgvector 原子入库、HNSW 索引与真实数据库集成测试。
- **完成**：
  - 新增 `app.rag.embeddings` 公共服务，复用现有 `EmbeddingProvider` 和 provider factory。
  - 按 `EMBEDDING_BATCH_SIZE` 切分请求，校验 provider 返回数量、provider 声明维度和每条向量的实际维度；空输入不调用 provider。
  - 文档入库维护 `processing → ready / failed`，全部向量成功后才在单个事务内删除旧切片并插入新切片；数据库异常回滚整篇替换。
  - 采用先删后插保证同一文档重处理幂等，原因和取舍见 ADR-0007。
  - 新增 `0002_document_chunks_hnsw_index`，使用 HNSW + `vector_cosine_ops`；HNSW、IVFFlat、余弦与 L2 的取舍见 ADR-0008。
  - 真实 ORM 测试发现并修复 `Message.created_at` 已存在于迁移但遗漏于模型映射的问题。
  - 集成测试使用 1024 维 Mock provider，不需要 API Key；数据库不可达时自动跳过，并在 teardown 精确清理测试用户、知识库、文档和切片。
- **修改文件**：`apps/api/app/rag/embeddings/**`、`apps/api/app/models/document.py`、
  `apps/api/app/models/conversation.py`、`apps/api/alembic/versions/0002_document_chunks_hnsw_index.py`、
  `apps/api/tests/test_embeddings.py`、`apps/api/tests/test_embeddings_integration.py`、
  `apps/api/tests/test_models.py`、`apps/api/pyproject.toml` 和项目状态文档。
- **运行命令与真实结果**：
  - `cd apps/api && .venv/bin/alembic upgrade head` → 真实库成功执行 `0001_initial_schema → 0002_document_chunks_hnsw_index`。
  - `cd apps/api && .venv/bin/alembic downgrade 0001_initial_schema && .venv/bin/alembic upgrade head` → 真实库索引降级/升级均成功，最终 `0002_document_chunks_hnsw_index (head)`。
  - `cd apps/api && .venv/bin/python -m pytest tests/test_embeddings.py` → **6 passed**。
  - `cd apps/api && .venv/bin/python -m pytest tests/test_embeddings_integration.py` → **2 passed**；真实执行解析、切分、批量向量化、写库、余弦检索、幂等和失败回滚。
  - `cd apps/api && .venv/bin/ruff check .` → **All checks passed!**
  - `cd apps/api && .venv/bin/ruff format --check .` → **58 files already formatted**。
  - `cd apps/api && .venv/bin/python -m pytest` → **62 passed**。
  - fixture 清理复查 → 测试专用 users / knowledge_bases / documents 记录均为 **0**。
- **当前边界**：本轮未实现 M1-05 检索服务或 M1-06 生成；集成测试只用 SQL 验证 pgvector 近邻排序。

---

## 2026-08-01（第三段） — Claude：M1-04 代码审查 + 接手 M1-04b/M1-05

- **任务**：M1-04 审查、M1-04b、M1-05、M1-06/07 修正

- **背景**：Codex 完成 M1-04 后，派发的第二轮（M1-04b + M1-05）执行中被中断，
  产出不完整——`retrieval/service.py` 已写但 M1-04b 安全修复完全没做，
  且提前实现了 M1-06/07（指令中明确要求不要提前做）。由 Claude 接手补完。

### 一、M1-04 审查结论：实现可靠，但有一处安全缺陷

独立复核确认 Codex 未虚报：集成测试是**真跑**（2 passed 而非 skipped，耗时 31.9s，
符合走隧道的网络往返），全量 62 passed，HNSW 迁移正确使用 `vector_cosine_ops`，
幂等采用先删后插且在事务内，先完成 embedding 再开事务（provider 失败时旧索引完好），
并用 `with_for_update` 加行锁。

**缺陷（已实测确认）**：`_mark_failed` 把 `str(exc)[:500]` 直接写入
`document.error_message`，而 SQLAlchemy 的 `StatementError.__str__` 会拼接
`[SQL: ...]` 与 `[parameters: ...]`，参数即 chunk 正文。构造一次外键违反实测：

```
异常类型: IntegrityError
str(exc) 总长度: 1241
是否包含文档正文: True
截断到 500 字符后仍含正文: False   ← 仅因 SQL 段较长而侥幸
```

该字段会经 API 返回给前端。交接文档明确禁止记录文档正文。

### 二、M1-04b 修复

新增 `safe_error_detail()`：对 `SQLAlchemyError` 取 `exc.orig` 首行，
**结构性**排除 SQL 与绑定参数，而非依赖长度截断。同时清理了 `embed_texts` 中
一段只有 `raise` 的空 `try/except`。

新增 `tests/test_error_redaction.py`（5 passed），断言正文、`[SQL:`、`[parameters:`
均不出现，同时保留异常类型与原因。

### 三、M1-05 修正：三处缺陷

1. **移除伪造分数**（见 ADR-0009）：检索对 `mock-embedding` 特判，用词法重叠
   覆盖真实余弦分数，会让 M4 评测产出虚假命中率。
2. **补 `ready` 状态过滤**：原实现只按 `knowledge_base_id` 过滤，
   `processing`/`failed` 文档残留的上一版切片会被检索到。
3. **阈值下推到 SQL**：原实现先 `LIMIT top_k` 再在 Python 过滤 `min_score`，
   低分结果会占掉名额，把本该入选的高分结果挤出 Top-K。改为
   `WHERE distance <= 1 - min_score`。

### 四、补测试：检索此前零覆盖

Codex 留下的 `test_retrieval_generation.py` 只测了 `citation_label` 字符串拼接
与参数校验，**没有任何测试引用 `VectorSearchService`**。

新增 `tests/test_retrieval_integration.py`（4 passed，真实库）：
- 余弦排序正确，分数与手工计算值一致（1.0 / 0.9938837 / 0.0）
- 引用元数据齐全（document_name、chunk_index、page_number、section_title）
- `processing` 文档的切片确实被排除
- `top_k=2` + 阈值 0.5 时，两条返回都合格（验证阈值下推）
- `EXPLAIN` 确认计划走 `ix_document_chunks_embedding_hnsw`
  （先 `SET LOCAL enable_seqscan = off`，排除"数据量小所以顺序扫描"的干扰；
  若算子与索引 ops 不匹配，索引会被静默忽略而功能测试照样通过）

关键做法：用 `StubEmbeddingProvider` 给定精确查询向量，而不是让 mock 生成哈希向量。
mock embedding 语义无关，用它断言"问年假就返回年假文档"是自欺欺人；
这里验证的是检索机制本身，与模型语义能力无关，因此可离线确定性断言。

新增 `tests/test_generation.py`（5 passed）：断言提示词确实携带证据正文与引用标签、
系统提示词包含防注入声明、**无证据时完全不调用模型**（防止其凭参数记忆编造企业事实）、
`confidence_threshold` 正确下传为 `min_score`。

### 五、验证结果（真实输出）

```
ruff check .            → All checks passed!
ruff format --check .   → 66 files already formatted
pytest                  → 81 passed in 69.66s
```

### 六、已知问题与遗留

- M1-06 尚缺交接文档要求的「10 道预设问题返回对应来源」验收，故标为 REVIEW 而非 DONE。
- M1-07 的拒答阈值默认 0.35 是拍脑袋值，未经评测校准，待 M4 用真实数据定。
- M1-06/07 属提前实现，未按里程碑节奏走，已在任务表注明责任划分。

- **下一位执行者**：Codex（M1-06 的 10 题验收）或 Claude（M2 前端）

- **建议下一步**：先补齐 M1-06 的 10 道预设问题验收，形成 M1 的完整闭环，再进 M2。

### 七、追加：演示路由的生产隔离（M1-08）

审查中发现 Codex 还提前实现了 API 层（`app/api/routes/demo_rag.py`、
`document_preview.py`，已挂载进 `main.py`），属 M2 范围。数据库里那条
`demo@enterprise-rag.local` 演示数据即由此产生。

上传大小限制是有的（`_save_upload` 流式读取，超限返回 413），这点没问题。
但两个路由**没有任何认证与配额控制**：任何人都能上传文件、触发文档解析和
模型调用。M5 的目标是部署到公网，靠"部署时记得关掉"不可靠。

处置：`APP_ENV=production` 时不挂载这两个路由，并加测试锁定
（生产下 `/demo/query` 与 `/documents/preview` 返回 404，`/health` 仍 200，
`/docs` 亦关闭）。最终 `pytest` **82 passed**。

---

## 2026-08-01（第四段） — Claude：提交 M1 成果 + M1-06 验收

- **任务**：git 提交、M1-06 验收

### 一、提交（应用户要求）

M1 全部成果分四个提交固化，提交前完整验证：后端 `pytest` 82 passed、
`ruff check`/`format` 通过；前端 `lint`/`typecheck`/`build` 通过、
`npm audit` 0 漏洞、Playwright e2e 2 passed。

```
e42b847 docs: M1 进展、架构决策与环境抢修记录
497220b feat(api,web): 文档实验台 —— 上传、解析预览与带引用问答
3f8c162 feat(rag): 向量化入库、Top-K 检索与带引用生成
c0cd9f2 feat(api): M1 数据模型、文档解析与结构化切分
585b1d5 chore: M0 工程骨架
```

提交过程中发现 Codex 还改动了前端（`page.tsx` +581 行）并新增 `lucide-react`
依赖、修改了交接文档状态行——均已验证可用后一并提交，交接文档状态更新至当前进度。

### 二、M1-06 验收：区分「机制」与「效果」

交接文档的 M1 完成标准是「给定演示文档，API 可以回答 10 个预设问题并返回对应来源」。
但当前没有任何 API Key，mock embedding 是确定性哈希向量、语义无关，
**用它计算命中率就是伪造指标**。因此把验收拆成两件事：

- **机制验收**（现在可做）：全链路能否跑通、返回结构是否完整可回溯、无依据时是否拒答
- **效果验收**（必须等真实 embedding）：检索到的来源对不对

新增内容：
- 演示语料扩充为三份虚构企业文档（员工手册、报销制度、IT 安全规范），
  覆盖多主题、含明确事实，便于出题
- `data/eval/m1-questions.json`：11 道题（9 道有依据 + 2 道语料中完全没有依据）
- `apps/api/scripts/run_m1_eval.py`：验收脚本，同一份脚本在配置真实 key 后
  可直接产出有效指标，也是 M4 评测的基础

### 三、验收结果（mock provider，真实输出）

```
[LIMIT] Q01~Q09 (有依据)  命中=False 来源=[]
[PASS]  Q10、Q11 (无依据) 拒答=True
--------------------------------------------------
失败题数          : 0
受 mock 限制未评估: 9
无依据拒答正确    : 2/2
标准来源命中      : 0/9
Embedding Provider: mock
```

9 道有依据题被判为 **limited 而非 fail**：mock 的哈希向量与查询的余弦相似度
接近 0，全部低于 0.35 阈值因而被拒答。这是 provider 的固有限制，不是链路缺陷。
把它记为 limited，是为了不把「待验证」粉饰成「已通过」，也避免被误判成 bug。

值得注意：这个结果恰恰印证了 ADR-0009 的判断——此前的 mock 特判正是用词法重叠
把这个真相盖住，让 mock 下的检索「看起来有效」。移除后，系统诚实地暴露了
「没有真实 embedding 就没有语义检索能力」这一事实。

脚本在 mock 模式下会显式打印警告，声明命中率不得写入简历或 RESUME_EVIDENCE。

### 四、修复的两个问题

1. 验收脚本初版用 `pool_pre_ping=True`，在连接复用时 ping 跑在非 greenlet 上下文，
   触发 `MissingGreenlet`；且清理沿用主流程会话，会话处于异常事务状态时清理失败。
   改为不开 pre_ping、并用全新会话清理。
2. 前几次失败运行残留了 5 组评测数据（users 由 1 涨到 6、chunks 涨到 76），
   已按 `eval-%@example.test` 清理干净。修复后复跑，运行前后数据库状态一致
   （users=1 docs=1 chunks=1），退出码 0。

### 五、遗留

- **M1-06 标 BLOCKED**：效果验收需要 `EMBEDDING_API_KEY`。这是 M1 唯一未达标项，
  阻塞原因是缺凭据而非代码缺陷。
- **M1-07 标 REVIEW**：「无依据必拒答」已验证 2/2；「有依据时不误拒」无法在 mock 下验证。
- 阈值 0.35 为拍脑袋默认值，待 M4 用真实数据校准。

- **建议下一步**：取得 SiliconFlow API Key → 改 `.env` 的 `LLM_PROVIDER` 与
  `EMBEDDING_PROVIDER` 为 `openai_compatible` → 重跑 `scripts/run_m1_eval.py`
  → 得到真实命中率后 M1 收尾，再进 M2。

---

## 2026-08-02 — Codex：M2-01a 认证与权限（仅后端）

- **任务**：实现 Cookie 会话认证、管理员权限、用户管理和种子管理员；严格不进入知识库、
  文档、对话/问答 API 或前端范围。

- **完成**：
  - 新增 Argon2id 密码哈希与 PyJWT 签发/校验，Token 只通过 `access_token` Cookie 下发，
    不进入响应体；Cookie 使用 `HttpOnly`、`SameSite=Lax`，生产环境增加 `Secure`。
  - 新增 `get_current_user` 与 `require_admin` FastAPI 依赖；缺 Cookie、过期/无效 Token、
    用户失效统一返回 401，普通成员访问管理员接口返回 403。
  - 实现 `POST /auth/login`、`POST /auth/logout`、`GET /auth/me`、
    `POST /admin/users`、`GET /admin/users`，重复邮箱统一返回 409。
  - 登录未知邮箱时仍校验固定 Argon2 哈希，使其与密码错误路径保持同一量级；两种失败响应
    完全一致，均为 `401 {"detail":"邮箱或密码错误"}`。
  - 从 `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` 幂等创建管理员；任一未配置时记录日志并
    跳过，已有用户不覆盖密码。`.env.example` 保持两项为空，避免产生已知默认账户。
  - `User.password_hash` 现有长度为 255，实测足够存 Argon2id 字符串，因此未新增无意义迁移；
    数据库迁移仍为 `0002_document_chunks_hnsw_index (head)`。
  - 新增认证集成测试，覆盖成功/失败登录、未知用户、缺 Cookie、过期 Token、成员 403、
    管理员创建/重复邮箱、种子幂等、生产 Cookie `Secure` 以及所有用户响应排除密码哈希。
  - 新增 `docs/API.md` 和 ADR-0010，记录 Cookie 相对 localStorage 的 XSS 收益、CSRF 面与
    当前 SameSite=Lax 取舍。实际配置解析得到 4 个显式 CORS 来源，不含 `*`。

- **范围确认**：未读取或修改 Claude 并行开发中的 `apps/web/`；未新增知识库 CRUD、文档管理、
  对话或问答 API；`/demo/*` 与 `/documents/preview` 路由实现保持原样。

- **运行命令与真实结果**：
  ```text
  cd apps/api && .venv/bin/ruff check .
  All checks passed!

  cd apps/api && .venv/bin/ruff format --check .
  74 files already formatted

  cd apps/api && .venv/bin/python -m pytest
  85 passed, 6 warnings in 191.80s (0:03:11)

  cd apps/api && .venv/bin/alembic current
  0002_document_chunks_hnsw_index (head)
  ```

- **警告说明**：6 条均来自现有依赖的弃用提示（FastAPI TestClient/httpx、PyMuPDF SWIG
  类型），没有测试失败或跳过。

---

## 2026-08-02 — Claude：M2-01 认证前端 + 环境重大故障排除

### 一、M2-01b 认证前端（与 Codex 的后端并行开发）

- 统一 HTTP 层 `src/lib/http.ts`：所有请求带 `credentials: "include"`，
  会话走 httpOnly Cookie，JS 读不到也就无法被 XSS 窃取
- 登录页、`AuthGuard` 路由守卫、`AppShell` 顶部导航与退出
- 用 Next 路由组 `(app)` 隔离受保护页面，登录页不受守卫拦截
- 实验台迁至 `/lab` 并适配外壳（移除其自带的 header 与嵌套 `<main>`），
  其中的 API 健康指示提升到顶栏，对所有页面生效
- `/kb`、`/chat` 为占位页，明确写出「已完成什么、还差什么、属于哪个里程碑」，
  而不是显示假装可用的空壳

### 二、对 Codex 后端认证的审查结论

实现质量高，未发现可利用漏洞：
- 登录时 `user is None` 检查在前，因此未知用户走 dummy hash 即使返回 True 也会被拒
- Cookie 属性齐全（httpOnly / secure 随环境 / SameSite=Lax），且 logout 的
  `delete_cookie` 参数与 set 时一致（否则删不掉）
- `UserResponse` 不含 `password_hash`；JWT 显式指定 algorithms 并要求 exp/sub

发现一处前后端契约不一致：后端 `display_name` 为 `str | None`（管理员建号时可不填），
前端类型写成了 `string`，会渲染出 "null"。已加 `displayNameOf()` 回退到邮箱前缀。

### 三、M2-01c CI 接入真实数据库

认证引入后 e2e 必须有用户表，原 CI 必挂。api 与 e2e 两个 job 各挂 pgvector service，
手工建扩展（service 容器不执行 `scripts/init-db.sql`）并执行迁移；
前端依赖改用 `npm ci`，避免上游发新版在无关改动上炸掉构建。

### 四、环境重大故障：项目位于 iCloud 同步目录

**现象**：测试从 70 秒退化到 40 分钟跑不完；模块导入时快时卡（同一句 import
有时 0.7 秒、有时超过 5 分钟）；全过程 CPU 0%；`git status` 与 `mv` 也会超时。

**误判与修正**：先后怀疑过 tiktoken 需要联网下载 BPE 文件、httpx 导入慢、
僵尸 pytest 进程。用 `faulthandler.dump_traceback_later` 转储调用栈，发现卡在
`fastapi/__init__.py` 的纯 Python 导入上——纯 Python 导入不可能慢，由此判断是
文件系统层面的问题。

**根因**：项目位于 `~/Desktop`，而该机器的桌面在 iCloud Drive 同步范围内。
`brctl status` 显示同步队列里正是 `.venv/site-packages` 这类海量小文件。
iCloud 反复同步导致文件读取间歇性阻塞。

**处置**：项目迁至 `~/dev/enterprise-rag-assistant`。迁移中 `mv` 跨 iCloud
边界失败，部分文件的数据块未落地，导致 134 个文件中约一半 `cat` 报
`Operation timed out (os error 60)`。所幸 `.git` 对象库完好，
`git cat-file` 能完整读出内容，遂用 `git clone` 从对象库重建干净工作区，
逐个校验 134 个文件均可读；中文文件名的 `项目交接文档.md` 单独用
`git cat-file -p` 取出恢复。**代码零丢失**。

**迁移前后对比**：

| 操作 | iCloud 目录下 | ~/dev 下 |
|---|---|---|
| `uv venv` | 超时失败 | 0.1 秒 |
| `npm ci` | 数分钟 | 3.6 秒 |
| `pytest`（85 项） | 40 分钟未跑完 | 1 分 49 秒 |
| `npm run e2e`（7 项） | 不稳定 | 19.4 秒 |

**遗留建议**：`~/CLAUDE.md` 中记录的 GitHub 项目默认根目录
`/Users/wind/Desktop/我的Git/GIthub项目` 同样位于 iCloud 同步范围内，
其他项目会遇到同样问题，建议一并迁出或关闭桌面同步。

### 五、验证结果（迁移后，真实输出）

```
后端  pytest                → 85 passed in 1:49
后端  ruff check / format   → 通过
前端  lint / typecheck      → 0 problems
前端  build                 → 成功，6 个路由
前端  npm audit             → 0 vulnerabilities
e2e   playwright            → 7 passed in 19.4s
```

e2e 覆盖：未登录跳转、根路径守卫、登录成功、退出后会话失效，
以及「密码错误」与「账号不存在」返回完全一致的提示（防用户枚举）。
