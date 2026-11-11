# 企业级 RAG 智能助手 · enterprise-rag-assistant

> 仓库名 `enterprise-rag-assistant` 直译即「企业级 RAG 助手」。
> RAG = Retrieval-Augmented Generation，检索增强生成：先从知识库检索资料，再让模型
> 基于检索到的资料作答，从而让答案有据可查。

面向企业内部知识库的问答系统：上传文档、建立知识库、基于知识库提问，**返回带原文引用与
来源位置的答案**；证据不足时明确拒答而非编造。

> **当前状态：M1 最小 RAG 闭环、M2 全栈认证/权限与 Agent 编排层、M3 MimirQ 检索中台集成已全部就绪**
> - 已可上传文档、建库、切片检索并生成带引用的答案；登录认证、时序对齐防枚举与管理员权限全栈打通。
> - 具备自主 Agent 手写编排循环与 AST 安全求值工具（ADR-0011）。
> - 具备 MimirQ 工业级混合检索中台微服务接入能力（BM25 + 向量召回 + Rerank 重排序，ADR-0012）。
> - 详细能力边界与全量 114 项验证结果见 [`docs/STATUS.md`](docs/STATUS.md)。
> - 本 README 中的所有命令均已在本机实际执行并通过。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · TanStack Query |
| 后端 | Python 3.13 · FastAPI · Pydantic v2 · pydantic-settings |
| 数据 | PostgreSQL 17 + pgvector + pg_trgm · Redis 7 |
| 检索中台 | 原生 pgvector 向量检索 + MimirQ 混合检索中台（BM25/Vector/Reranker，微服务解耦） |
| 模型 | OpenAI 兼容 API（SiliconFlow / DeepSeek / vLLM 等）+ 内置 Mock |
| 测试 | pytest · Playwright · ruff · ESLint · tsc |
| 交付 | Docker 多阶段构建 · Docker Compose · GitHub Actions |

## 已实现能力

### 检索与问答

- 向量化入库：切片经 embedding 写入 `pgvector`，`VECTOR(1024)` 列 + HNSW 索引。
- Top-K 检索：余弦相似度排序，可配置相似度阈值。
- 带引用生成：答案附原文出处（文档、页码、标题上下文），可回溯到具体切片。
- **无依据拒答**：检索证据不足时明确拒答，不编造企业事实。
- 前端「文档实验台」：上传 → 解析预览 → 切分结果 → 带引用问答的完整链路。
- **MimirQ 混合检索中台集成（路线 B）**：支持通过 `MIMIRQ_ENABLED=true` 环境变量一键接入开源企业检索中台 MimirQ，获得 BM25 + Dense Vector + Cross-Encoder Rerank 混合召回与证据胶囊回溯能力，支持与本地 pgvector 检索平滑热切换（见 ADR-0012）。

### Agent 工具调用与手写编排

- 协议扩展：`LLMProvider` 协议增加 `complete_with_tools`，解耦业务逻辑与模型厂商 API（ADR-0011）。
- 手写编排循环：受控循环上限（默认 4 步）、寒暄判定短路、工具执行异常转换为可读反馈。
- 安全计算器工具：使用 Python `ast` 白名单求值（仅允许算术四则运算与括号），严防代码注入。
- 确定性 Mock 驱动：支持零成本、离线、确定性断言整个 Agent 工具调用全生命周期。

### 认证与权限

- Argon2id 密码哈希 + PyJWT 签发；Token 仅通过 `HttpOnly` + `SameSite=Lax` Cookie 下发，
  不进入响应体，生产环境追加 `Secure`。
- `get_current_user` / `require_admin` 依赖；401 与 403 语义分离。
- 登录失败路径做了时序对齐：未知邮箱同样校验固定 Argon2 哈希，与密码错误保持同一量级，
  两种失败响应完全一致，避免用户枚举。
- 管理员账号从环境变量幂等创建；未配置时跳过，不产生已知默认账户。
- 取舍理由（Cookie vs localStorage 的 XSS 收益与 CSRF 面）见 ADR-0010。

### 前端页面

`/login` 登录 · `/kb` 知识库 · `/chat` 问答 · `/lab` 文档实验台

## 当前文档解析能力

- PDF：按页提取文本并保留从 1 开始的页码；扫描件 OCR 尚未加入。
- DOCX：按原顺序提取标题、段落和表格，并保留标题上下文。
- Markdown：使用 CommonMark 解析标题、可见正文、列表和代码块。
- TXT：支持 UTF-8、GB18030、Big5，并保留空行分隔的段落。
- 默认单文件上限 50 MiB；空文档、损坏文件、加密 PDF、旧版 `.doc` 和未知格式会返回统一解析错误。

## 当前文档切分能力

- 入口：`app.rag.chunking.chunk_document(parsed_document, ...)`；已有块列表可使用 `chunk_blocks(...)`。
- 默认使用 `tiktoken` 的 `cl100k_base` 计数；`max_tokens`、`chunk_overlap` 和最小 Token 数均可配置。
- 页码和标题上下文是硬边界；同一上下文内优先按段落拼接，过长段落先按句/行组织，再按 Token 窗口兜底。
- 每个不可变 `Chunk` 保留稳定索引、Token 数、页码、标题和来源 block 索引，便于后续引用回溯。

## 快速开始

前置依赖：Python 3.13、Node 22、[uv](https://docs.astral.sh/uv/)、Docker Desktop。

```bash
git clone <仓库地址> enterprise-rag-assistant
cd enterprise-rag-assistant

make setup      # 生成 .env、安装前后端依赖
make up-infra   # 启动 PostgreSQL(pgvector) 与 Redis
make dev        # 前后端热重载，Ctrl-C 一并退出
```

启动后：

- 前端 http://localhost:3000
- 后端文档 http://localhost:8000/docs

**无需任何 API Key**：默认使用 mock provider，测试与 CI 不需要任何模型服务凭据。

> **注意**：切分模块使用 `tiktoken` 的 `cl100k_base`，首次运行会从
> `openaipublic.blob.core.windows.net` 下载 BPE 文件并缓存到临时目录。
> 该地址不可达时，首次 `pytest` 会长时间阻塞在收集阶段。离线或网络受限环境请预先设置
> `TIKTOKEN_CACHE_DIR` 并放入已下载的编码文件。缓存建立后加载耗时约 0.1 秒。

### 全部命令

```bash
make help       # 列出所有命令
make setup      # 一次性环境准备
make dev        # 开发模式（前后端热重载）
make lint       # ruff + ESLint + tsc
make test       # 后端测试
make e2e        # 端到端测试（首次需先跑 make e2e-install）
make up         # 以容器方式启动全栈
make down       # 停止容器（保留数据）
make clean      # 停止容器并删除数据卷
```

## 接入真实模型

编辑 `.env`（该文件已被 `.gitignore` 排除，切勿提交）：

```bash
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=你的密钥
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_API_KEY=你的密钥
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024          # 必须与模型真实维度一致
```

换成任何 OpenAI 兼容服务（DeepSeek、通义、自建 vLLM）都只需改这几个变量，不改代码。
设计说明见 [ADR-0001](docs/DECISIONS.md)。

## 生产部署（单机 VPS）

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

生产覆盖层会关闭数据库与 Redis 的端口暴露、关闭 `/docs` 与 `/openapi.json`、
启用日志轮转。理由见 [ADR-0002](docs/DECISIONS.md)。

## 项目文档

| 文档 | 内容 |
|---|---|
| [项目交接文档.md](项目交接文档.md) | 单一事实来源：定位、范围、里程碑、协作规则 |
| [docs/STATUS.md](docs/STATUS.md) | 当前可运行状态、已验证结果、已知问题 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构图、模块职责、关键约束 |
| [docs/DECISIONS.md](docs/DECISIONS.md) | 架构决策记录（ADR） |
| [docs/TASKS.md](docs/TASKS.md) | 任务编号、负责人、验证方式 |
| [docs/SESSION_LOG.md](docs/SESSION_LOG.md) | 每次会话的改动、命令与真实结果 |

## 安全约定

- 所有密钥只通过环境变量加载，仓库中不出现任何真实凭据。
- `.env`、上传文件、数据库卷、日志、模型缓存均已在 `.gitignore` 中排除。
- 容器以非 root 用户运行。
- 生产环境关闭交互式 API 文档。
- Provider 抛出的错误经过脱敏，不携带 URL、请求头或文档正文。
- 公开演示只使用虚构企业资料。

## 路线图

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M0 | 工程骨架、编排、CI | 完成 |
| M1 | 最小 RAG 闭环：解析 → 切分 → 向量化 → 检索 → 带引用生成 | 完成（效果指标待真实模型） |
| M2 | 全栈产品：登录、知识库管理、流式问答、引用预览 | 进行中（M2-01a 认证后端完成） |
| M3 | Agent 与工具调用：Function Calling、LangGraph 编排、会话记忆 | 未开始 |
| M4 | 评测：≥30 题评测集、命中率、拒答表现、延迟 | 未开始（M1 已备 11 题基线集与评测脚本） |
| M5 | 部署与演示：VPS 上线、架构图、录屏 | 未开始 |

## 关于评测指标

`apps/api/scripts/run_m1_eval.py` 与 `data/eval/m1-questions.json`（11 题，含 2 题无依据题）
已就绪，但**在 mock provider 下不产出有效的命中率**：mock embedding 是确定性哈希向量、
语义无关，用它算命中率等同于伪造指标。脚本在 mock 模式下会显式打印警告。

因此当前严格区分两类结论：

- **机制验收**（已完成）：链路能否跑通、引用是否完整可回溯、无依据是否拒答（2/2 正确）
- **效果验收**（待真实 embedding）：检索到的来源是否正确、命中率、延迟

配置真实 key 后直接运行该脚本即可产出有效指标。

## 许可证

[MIT](LICENSE)
