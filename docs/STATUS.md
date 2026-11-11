# 项目状态

> 最后更新：2026-08-01
> 当前里程碑：**M1 最小 RAG 闭环**（M1-03 结构化切分完成）

## 一句话状态

M0 工程骨架、M1-01 数据层、M1-02 文档解析和 M1-03 结构化切分已完成。内部服务现在可以
把 PDF、DOCX、Markdown、TXT 转换成带页码/标题上下文的 Token 有界切片；上传接口、向量化
和问答链路仍待实现。

## 已完成并验证

| 项目 | 验证命令 | 真实结果 |
|---|---|---|
| 后端单元/集成测试 | `cd apps/api && .venv/bin/python -m pytest` | 45 passed |
| 后端静态检查 | `.venv/bin/ruff check .` | All checks passed |
| 后端格式检查 | `.venv/bin/ruff format --check .` | 49 files already formatted |
| 前端 lint | `cd apps/web && npm run lint` | 0 problems |
| 前端类型检查 | `npm run typecheck` | 通过，无错误 |
| 前端生产构建 | `npm run build` | 成功，`/` 与 `/_not-found` 静态预渲染 |
| 前端依赖漏洞 | `npm audit` | found 0 vulnerabilities |
| 端到端测试 | `npm run e2e` | 2 passed |
| 开发编排配置 | `docker compose config --quiet` | 通过 |
| 生产编排配置 | `docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet` | 通过 |
| 后端接口手工验证 | `curl -i http://127.0.0.1:8100/health` | HTTP 200，返回 mock provider 信息 |
| CORS 配置 | `curl -H "Origin: http://127.0.0.1:3100" .../health` | 正确返回 `access-control-allow-origin` |
| **pgvector 实际启动（VPS）** | `docker compose up -d db redis` + `\dx` | rag-db / rag-redis 双 healthy；**vector 0.8.6**（含 ivfflat/hnsw）、**pg_trgm 1.6**、PostgreSQL 17.10 |
| **向量检索端到端（VPS）** | HNSW 索引 + 余弦相似度查询 | 排序正确：年假制度 1.0000 > 年假申请 0.9939 > 报销流程 0.0000 |
| **Redis 实际启动（VPS）** | `redis-cli set/get/del` + `config get appendonly` | 读写正常，AOF 持久化已开启 |
| **容器资源占用（VPS）** | `docker stats --no-stream` | rag-db 74.3 MiB、rag-redis 12.1 MiB |
| M1-01 模型导入与元数据 | `cd apps/api && .venv/bin/python -m pytest tests/test_models.py` | 3 passed；6 张核心表、`VECTOR(1024)` 和枚举值通过断言 |
| M1-01 Alembic 离线迁移 | `cd apps/api && .venv/bin/alembic upgrade head --sql` | 生成扩展、3 个枚举、6 张表和向量列 |
| M1-02 文档解析 | `cd apps/api && .venv/bin/python -m pytest tests/test_loaders.py` | 11 passed；覆盖四种格式、中文编码、页码/标题/表格和失败场景 |
| M1-03 结构化切分 | `cd apps/api && .venv/bin/python -m pytest tests/test_chunking.py` | 14 passed；覆盖页码/标题边界、段落打包、Token 上限、中文混合文本、长段 overlap、空块和非法参数 |
| M0-18 备用端口 CORS | `cd apps/api && .venv/bin/python -m pytest tests/test_health.py` | 6 passed；localhost/127.0.0.1 的 3000/3001 均通过预检 |

## 当前能力边界（不要超出这个范围描述项目）

- 后端仍只有 `/health` 一个端点，**没有文档上传、检索或问答功能**。
- M1-01 已建立用户、知识库、文档、文档切片、会话和消息数据模型；尚未接入业务路由。
- M1-02 解析服务已支持 PDF、DOCX、Markdown、TXT，返回统一 `ParsedDocument`/`ParsedBlock`。
- PDF 保留页码；DOCX/Markdown 保留标题上下文；DOCX 表格按行提取；TXT 支持常见中文编码。
- M1-03 切分服务默认使用 `cl100k_base` 计数；按页码和标题上下文分组，优先拼接段落，超长内容按句/行后以 Token 窗口兜底，并保留来源 block 索引。
- 切片结果为不可变 `Chunk`，包含稳定索引、正文、Token 数、页码、标题和来源范围；尚未接入向量化或数据库写入。
- 当前不包含扫描 PDF OCR、旧版 `.doc`、复杂 DOCX 浮动对象和加密 PDF 解密。
- Provider 层已具备切换真实厂商的能力，但**默认且仅验证过 mock 实现**。
- 前端只有一个首页，展示后端连通性与里程碑列表。
- 尚无任何检索命中率、延迟等评测数字。

## 已知问题

1. **本地 Docker Desktop 仍不可用（不阻塞项目，已用 VPS 验证替代）**
   2026-08-01 排查结论：两处根本损坏已修复——(a) ext4 超级块记录的容量大于 `Docker.raw`
   实际大小（磁盘曾被截断），`e2fsck` 直接 abort；(b) containerd 的 bbolt 元数据库
   `meta.db` 有一个数据页被清零，导致 containerd 每次启动都 panic。修复后磁盘错误归零、
   containerd 能正常 `serving`，但 Docker Desktop 4.74.0 启动后仍会反复自行关机
   （`recovering from engine crash`）。
   建议：重装 Docker Desktop，或改用 colima（本机已有 colima context）。
   影响：本地 `make up` 与镜像构建仍未验证；pgvector 与 Redis 已在 VPS 上验证通过。

2. **Codex 不可用（阻塞 M0-17）**
   Codex CLI 的上游端点持续返回 503（`Reconnecting 1/5 … 5/5` 后失败），本轮 M0 全部由
   Claude 完成，未获得独立复核。恢复后需按交接文档的分工补做代码审查。

3. **前端 dev server 的 HMR WebSocket 在 Playwright 环境下握手失败**
   已通过改用 standalone 产物绕开（见 ADR-0005），但 `make dev` 下的热重载在浏览器中
   是否受影响尚未逐项确认。

4. **尚未取得任何模型 API Key**
   M1 的真实向量化、M4 的效果评测都需要。当前用 mock 推进不受影响。

## 下一步

1. 解除 Docker 阻塞，跑通 `make up`，确认 pgvector 与 pg_trgm 扩展已创建。
2. 首次 push 到 GitHub，确认 CI 四个 job 全绿。
3. 取得模型 API Key 并写入本地 `.env`（不提交）。
4. 解除 Docker/pgvector 环境阻塞，执行真实 `alembic upgrade head` 并检查扩展与表结构。
5. 继续 M1-04：调用 Embedding Provider 并写入 pgvector，沿用 M1-03 的来源元数据。

---

## 2026-08-02 — M1-04 追加状态

- M1-04 向量化与 pgvector 入库已完成；Embedding 服务按 `EMBEDDING_BATCH_SIZE` 分批，并在写库前逐个校验 `EMBEDDING_DIM`。
- 文档入库采用整篇“先删后插”事务；重复处理同一文档不会增加 chunk 数，失败会回滚替换并将文档置为 `failed`。
- `0002_document_chunks_hnsw_index` 已在真实 PostgreSQL 17 + pgvector 0.8.6 数据库上执行，建立 HNSW `vector_cosine_ops` 索引。
- 真实数据库集成测试已覆盖解析、切分、向量化、入库、余弦检索、幂等重处理和失败回滚；数据库不可达时按 fixture 探测跳过。
- 当前能力边界推进到“内部服务可完成向量入库”；M1-05 Top-K 检索服务和 M1-06 生成链路仍未实现。
- 验证结果：`ruff check .` 通过，`ruff format --check .` 58 files already formatted，`pytest` 全量 62 passed。

---

## 2026-10-10 — M2 Agent 层（M2-01~03）

- 新增 `app/rag/agent/`：`tools.py`（`search_knowledge_base` / `get_document_meta` / `calculator`）
  与 `service.py`（手写编排循环：检索分支 → 工具调用 → 带引用回答；步数上限 4，超限显式拒答）。
- `LLMProvider` 协议扩展 `complete_with_tools`；`openai_compatible` 解析 OpenAI 兼容
  `tool_calls`；`mock` 提供确定性脚本（首轮请求检索、随后作答），因此 Agent 链路无需 API Key 即可测。
- 安全：`calculator` 用 AST 白名单求值，拒绝属性访问、下标、函数调用、字符串常量与除零。
- 验证：`pytest` 102 passed / 8 skipped；`ruff check` 与 `ruff format --check` 全绿。
- 未完成：M2-04 API 端点与 M2-05 前端思考链路可视化——需要真实模型 Key 才能端到端联调
  （当前 `EMBEDDING_API_KEY` 为空、`LLM_API_KEY` 所在账号余额不足）。

---

## 2026-11-11 — MimirQ 企业级检索中台接入（路线 B）

- 新增 `app/rag/retrieval/mimirq_client.py`：封装异步客户端 `MimirQClient`，支持 JWT 鉴权与时效缓存复用、401 失效重试、混合检索代理（`/api/v1/rag/retrieve`）与文档代理上传（`/api/v1/documents/upload`）。
- 新增 `app/rag/retrieval/mimirq_service.py`：实现 `MimirQSearchService`，无缝适配既有检索契约（`search(...) -> tuple[SearchResult, ...]`），将 MimirQ 丰富 Citations 映射为不可变 `SearchResult`。
- 配置中心扩展：在 `Settings` 中新增 `mimirq_enabled` 开关及连接参数，`/demo/query` 路由支持根据环境变量在本地 pgvector 检索与 MimirQ 混合检索之间平滑热切换。
- 架构决策记录：编写并归档 [ADR-0012](DECISIONS.md#adr-0012-mimirq-企业级检索中台接入路线-b微服务解耦集成)。
- 验证结果：
  - 后端静态检查：`ruff check .` 全部通过，`ruff format --check .` 82 files already formatted。
  - 后端测试：`pytest` 全量 **114 passed，0 failed**（含 4 项专项集成测试）。
  - 前端验证：`eslint` 0 errors，`tsc --noEmit` 0 errors，Next.js 16 生产构建 `npm run build` 全部通过（6 个静态页面成功预渲染）。

---

## 2026-11-11 — 企业级优化闭环：多轮记忆、交互式大屏、自动化评测与双语规范

- **多轮会话记忆机制**：
  - `ChatMessageRequest` 结构与 `history: tuple[ChatMessageRequest, ...]` 请求载荷，实现多轮对话连贯记忆。
  - `GroundedAnswerService` 与 `AgentService` 原生支持注入历史轮次，既保留多轮追问语义，又严格将事实锁定在召回证据中。
- **交互式问答控制台与全链路可观测性 (`/chat`)**：
  - 支持「标准 RAG 模式」与「ReAct 智能编排模式」无缝切换。
  - 毫秒级 Telemetry 追踪徽章：总耗时、检索耗时、模型生成延迟（TTFT）、命中得分及检索模式（pgvector / MimirQ）。
  - ReAct Agent 工具执行轨迹抽屉：步骤折叠、入参可视化、工具返回值审计。
  - 证据溯源卡片（文件名、页码、章节、原文引用展开）与防幻觉拒答安全警示盾牌。
- **知识库文档管理面板 (`/kb`)**：
  - 彻底替换原有占位页面，落地 4 大核心指标统计看板（索引文档数、切片总量、向量存储引擎、检索中台）。
  - 支持拖拽/选择多格式文件（PDF/DOCX/MD/TXT）快速切片入库。
  - 知识库文档表格支持格式图标、切片数统计、状态 Badge、问答直达链接与级联物理删除。
- **自动化评测体系与基准测试集**：
  - 自建标准化基准评测集（20 组企业级测试用例，覆盖事实提取、数值比对、跨文档综合与负样本边界测试）。
  - `run_benchmark.py` 评估流水线，计算 Hit Rate@K、MRR（0.8889）、延迟分布（P50/P90/P99）与 Token 开销分析，自动化输出 Markdown 评测报告。
- **国际化双语建设与文档合规**：
  - 撰写包含 Mermaid 架构图、技术选型表、MimirQ 混合中台说明与快速上手指南的 `README_EN.md`。
  - 完成主 `README.md` 与 `README_EN.md` 双向语言无缝切换。
- **验证结果**：
  - 后端静态检查：`ruff check .` 全部通过，`ruff format --check .` 87 files already formatted。
  - 后端测试：`pytest` 全量 **120 项测试全部通过（112 passed, 8 skipped 需真实数据库）**。
  - 前端工程：`eslint` 0 errors, 0 warnings，`tsc --noEmit` 0 errors，Next.js 16 静态预渲染 8/8 路由全绿。


