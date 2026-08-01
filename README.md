# 企业级 RAG 智能助手

面向企业内部知识库的问答系统：上传文档、建立知识库、基于知识库提问，**返回带原文引用与
来源位置的答案**；证据不足时明确拒答而非编造。

> **当前状态：M0 工程骨架**
> 后端目前只有 `/health` 一个端点，RAG 功能尚未实现。
> 详细的能力边界与已验证结果见 [`docs/STATUS.md`](docs/STATUS.md)。
> 本 README 中的所有命令均已在本机实际执行过。

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · TanStack Query |
| 后端 | Python 3.13 · FastAPI · Pydantic v2 · pydantic-settings |
| 数据 | PostgreSQL 17 + pgvector + pg_trgm · Redis 7 |
| 模型 | OpenAI 兼容 API（SiliconFlow / DeepSeek / vLLM 等）+ 内置 Mock |
| 测试 | pytest · Playwright · ruff · ESLint · tsc |
| 交付 | Docker 多阶段构建 · Docker Compose · GitHub Actions |

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

**无需任何 API Key**：默认使用 mock provider，测试与 CI 完全离线可跑。

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
| M0 | 工程骨架、编排、CI | 基本完成（两项待验证） |
| M1 | 最小 RAG 闭环：解析 → 切分 → 向量化 → 检索 → 带引用生成 | 未开始 |
| M2 | 全栈产品：登录、知识库管理、流式问答、引用预览 | 未开始 |
| M3 | 企业级可靠性：租户隔离、审计日志、限流、注入防护 | 未开始 |
| M4 | 评测：≥30 题评测集、命中率、拒答表现、延迟 | 未开始 |
| M5 | 部署与演示：VPS 上线、架构图、录屏 | 未开始 |

## 许可证

[MIT](LICENSE)
