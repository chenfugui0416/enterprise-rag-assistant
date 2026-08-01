# 架构决策记录（ADR）

> 规则见「项目交接文档.md」。以下情况必须先写 ADR 再改代码：更换核心框架、更换向量库、
> 引入编排框架、更换认证方案、引入消息队列或云服务、调整租户隔离方式、删除已公开承诺的
> 功能、新增显著拉长周期的功能。

每条 ADR 至少包含：背景、决定、备选方案、理由、代价、回滚方式。

---

## ADR-0001 模型 Provider 采用 OpenAI 兼容接口抽象，并内置 Mock 实现

- 日期：2026-08-01
- 状态：已采纳

**背景**

项目需要调用生成模型与 Embedding 模型。若直接在业务代码里写死某一家 SDK，换厂商就要
改动检索与生成链路；同时项目启动时尚未取得任何 API Key，而 CI 不应依赖付费外部服务。

**决定**

1. 在 `app/rag/providers/base.py` 定义 `EmbeddingProvider` 与 `LLMProvider` 两个 Protocol，
   业务代码只依赖协议。
2. 提供两套实现：`openai_compatible`（适配任何暴露 `/chat/completions` 与 `/embeddings`
   的服务）与 `mock`（确定性、离线、零成本）。
3. 通过 `LLM_PROVIDER` / `EMBEDDING_PROVIDER` 环境变量切换，默认 `mock`。
4. 换厂商只改 `*_BASE_URL` / `*_API_KEY` / `*_MODEL` 三个变量，不改代码。
5. 示例配置指向 SiliconFlow（`https://api.siliconflow.cn/v1`，Embedding 用 `BAAI/bge-m3`），
   任何文件都不得写入真实 Key。

**备选方案**

- 直接用 OpenAI 官方 SDK：绑定单一厂商，国内访问与计费均不便。
- 引入 LangChain 的 Provider 层：为了一层抽象引入庞大依赖树，与 MVP 的克制原则冲突；
  按交接文档，编排框架要到 Agent 阶段再评估。
- 只做真实 Provider，不做 Mock：无 Key 时无法开发，CI 必然依赖外部服务且产生费用。

**理由**

Mock Provider 的确定性（同输入必定同输出）使切分、入库、检索、引用装配等环节可以被
断言，这些环节的正确性本来就与模型语义能力无关。真正需要语义能力的只有 M4 效果评测。

**代价**

- 多一层间接调用，排查上游问题时需多看一层。
- Mock 不具备语义能力，不能用于评测；必须在文档中明确标注，避免误当作效果证据。
- 不同厂商对 OpenAI 协议的兼容度有差异（如 embedding 返回顺序、维度），需在 Provider
  层做防御（已实现：按 `index` 排序、维度校验）。

**回滚方式**

删除 `providers/` 下的具体实现，业务代码保持依赖协议不变，成本可控。

---

## ADR-0002 部署目标为单机 VPS + Docker Compose

- 日期：2026-08-01
- 状态：已采纳

**背景**

M5 需要一个公开可访问的演示地址。候选方案包括自有 VPS、Vercel + Railway 托管、
腾讯 CloudBase。

**决定**

采用自有 VPS + Docker Compose 单机部署。编排拆为两层：`docker-compose.yml`（开发）
与 `docker-compose.prod.yml`（生产覆盖层，关闭数据库端口暴露、启用日志轮转、
`APP_ENV=production`）。不引入 Kubernetes。

**备选方案**

- Vercel + Railway：部署快，但前后端被平台切开，数据库需另接托管服务，架构叙述被
  平台细节稀释，且冷启动影响演示体验。
- 腾讯 CloudBase：国内访问快，但 pgvector 支持需另行确认，可能被迫更换向量方案。

**理由**

单机 Compose 与本地开发环境同构，「新电脑按 README 可运行」与「线上能跑」是同一套配置，
这正是项目要证明的工程能力。

**代价**

需要自行处理域名、TLS、备份与监控；单机无高可用（这一点不得在简历中包装为「高可用」）。

**回滚方式**

镜像本身与平台无关，改用任何支持容器的平台只需替换编排层。

---

## ADR-0003 目录与仓库统一命名为 enterprise-rag-assistant

- 日期：2026-08-01
- 状态：已采纳

**背景**

原目录名为「企业级 RAG 助手」，含中文与空格。

**决定**

目录与未来 GitHub 仓库名统一为 `enterprise-rag-assistant`。README 与界面标题保留中文
项目名「企业级 RAG 智能助手」。

**理由**

路径中的空格与非 ASCII 字符会影响 Docker 卷挂载、CI 工作目录、shell 脚本引用。越早改
成本越低。

**代价**

一次性重命名；本文档之前的路径引用需同步更新。

**回滚方式**

`mv` 即可，无代码依赖硬编码路径。

---

## ADR-0004 前端服务端状态在 M0 就引入 TanStack Query

- 日期：2026-08-01
- 状态：已采纳

**背景**

交接文档已把 TanStack Query 列为默认方案，原计划 M2 再引入。M0 用 `useEffect` +
`useState` 手写请求时，React 19 的 `react-hooks/set-state-in-effect` 规则报错：effect
内同步调用 setState 会触发级联渲染。该规则的静态分析无法识别 `await` 边界，绕过它需要
写出更别扭的代码。

**决定**

M0 即引入 `@tanstack/react-query`，在 `src/app/providers.tsx` 提供 QueryClient。

**备选方案**

- 关闭该 lint 规则：为了一处代码放宽全局质量门，不划算。
- 改用 Server Component 直接取数：容器内网地址与浏览器地址不同，且「重新检测」按钮需要
  客户端交互。

**理由**

反正是既定方案，提前引入既解决当下问题，又让后续的加载态、错误态、重试、缓存有统一处理。

**代价**

M0 多一个运行时依赖。

**回滚方式**

改回手写 fetch 并调整该 lint 规则。

---

## ADR-0005 e2e 针对 standalone 生产产物运行，而非 dev server

- 日期：2026-08-01
- 状态：已采纳

**背景**

首次接入 Playwright 时，针对 `next dev` 运行的用例失败：页面 SSR 正常但客户端未 hydrate，
`/health` 请求根本没有发出，控制台显示 HMR WebSocket 握手失败
（`ERR_INVALID_HTTP_RESPONSE`）。

**决定**

Playwright 的 `webServer` 先执行 `npm run build`，再按与 `apps/web/Dockerfile` 相同的方式
拷贝 `.next/static` 与 `public`，最后运行 `node .next/standalone/server.js`。
e2e 使用独立端口（前端 3100、后端 8100），避免与 `make dev`（3000/8000）冲突。

**备选方案**

- 继续用 dev server：不稳定，且测的不是真实产物。
- 用 `next start`：与 `output: standalone` 不兼容，Next 会明确警告。

**理由**

e2e 应当验证真正要部署的产物。顺带覆盖了 CORS 配置——这是本地能跑、容器里却常出问题的
一环。

**代价**

每次 e2e 需要一次生产构建，耗时增加。

**回滚方式**

改回 dev server 命令即可。
