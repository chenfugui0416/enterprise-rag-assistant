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

---

## ADR-0006 M1-03 使用 tiktoken 作为默认切分计数器

- 日期：2026-08-01
- 状态：已采纳

**背景**

切片上限必须与后续 Embedding/生成链路使用的 Token 概念一致。字符数或字节数对中文、英文和
混合文本的估算偏差明显，也无法稳定验证 overlap。

**决定**

`app.rag.chunking` 默认使用 `tiktoken` 的 `cl100k_base` 编码，配置项允许显式切换编码；通过
小型 `Tokenizer` 协议注入替代实现，切分模块不依赖具体模型 Provider。

**备选方案**

- 字符数近似：零依赖，但不同语言的上限误差不可控。
- 在切分模块中直接调用 Embedding Provider：计数与模型可能匹配，但引入网络依赖并破坏分层。

**代价**

增加一个运行时依赖和少量编码缓存；实际 Embedding 模型若采用不同 tokenizer，需要在配置中
切换编码并重新验证上限。

**回滚方式**

实现一个满足 `Tokenizer` 协议的本地计数器，或将默认编码替换为目标模型对应编码，不改变
`Chunk` 输出契约。

---

## ADR-0007 M1-04 使用先删后插实现文档切片幂等

- 日期：2026-08-02
- 状态：已采纳

**背景**

同一文档可能因为重试、切分参数调整或重新生成向量而被重复处理。`document_chunks` 的唯一约束只能阻止重复索引，不能清理旧版本的切片。

**决定**

采用“先生成并校验全部向量，再在一个数据库事务中删除该文档旧切片并插入新切片”的策略。文档状态在处理前置为 `processing`，整篇替换成功后为 `ready`，任意 provider 或数据库异常回滚替换并将文档标记为 `failed`。

**备选方案**

- upsert：需要为内容哈希和版本变化设计额外约束，旧切片清理更复杂。
- 内容哈希去重：同一内容可复用，但切分参数变化时旧切片仍可能残留。

**理由**

整篇替换符合文档索引的原子语义，实现简单，能够保证重试后 chunk 数和索引内容与当前解析结果一致。向量请求放在替换事务外，避免远程调用长时间占用数据库连接。

**代价**

重处理期间会短暂保留旧切片；最终替换事务提交后才切换到新版本。若进程在 `processing` 状态异常退出，运维任务需要按状态重新调度。

---

## ADR-0008 M1-04 使用 HNSW 与余弦距离建立 pgvector 索引

- 日期：2026-08-02
- 状态：已采纳

**决定**

为 `document_chunks.embedding` 建立 HNSW 索引，操作符类使用 `vector_cosine_ops`。Embedding 服务在写库前强制校验 `EMBEDDING_DIM`，Mock 向量和目标 embedding 均按余弦相似度语义处理。

**理由**

HNSW 在查询时不需要先训练聚类，数据持续增量写入时更适合文档知识库；在中小规模数据集上通常能以较好的召回率换取稳定的低延迟。IVFFlat 需要选择 lists 并在插入数据后维护聚类，适合规模更大且可接受训练/调参成本的场景。

余弦距离对归一化 embedding 只关注方向，降低文本长度和向量模长差异带来的影响；L2 距离会同时受模长影响，而当前 Provider 契约和检索目标都是语义方向相似度，因此选余弦。若未来模型明确要求非归一化向量或距离校准，再单独评估 `vector_l2_ops`。

**回滚方式**

回滚 `0002_document_chunks_hnsw_index` 迁移即可删除索引，不影响向量列和已有数据。

---

## ADR-0009 生产代码不得按 Provider 名字分支

- 日期：2026-08-01
- 状态：已采纳

**背景**

M1-05 与 M1-06 的初版实现里出现了两处按 provider 名字判断的分支：

```python
# 检索：mock 时用词法重叠覆盖真实的余弦分数
if self.embedding_service.provider.model_name == "mock-embedding":
    score = max(score, _lexical_similarity(query, chunk.content))

# 生成：mock 时跳过提示词装配，直接拼接首条证据
if self.llm_provider.model_name == "mock-llm":
    answer = f"根据知识库中最相关的资料：{retrieved[0].content}..."
```

动机可以理解——让离线演示"看起来有效果"。但代价有两个，都很严重：

1. **制造覆盖假象**。所有测试都跑 mock，而 mock 走的是另一条分支，
   于是真实厂商实际使用的提示词装配逻辑从未被任何测试执行过。
   当时全量 67 passed，但生成链路的真实路径覆盖率是 0。
2. **污染指标可信度**。检索处用词法重叠伪造出的分数，与真实语义相似度
   共用同一个 `score` 字段、无法区分。M4 评测若在 mock 下运行，会产出
   看似合理实则虚假的命中率——这与交接文档「禁止写入没有测量过的百分比」
   直接冲突。

**决定**

生产代码路径中禁止出现 `provider.model_name == "..."` 之类的分支。
所有 provider 必须走完全相同的代码路径；差异只允许存在于 provider 实现内部。

需要确定性行为时，用测试替身（stub/fake）注入，而不是在业务代码里开后门。
例如 `tests/test_retrieval_integration.py` 用 `StubEmbeddingProvider` 给定精确的
查询向量，从而断言排序与阈值；`tests/test_generation.py` 用 `RecordingLLMProvider`
捕获 messages，从而断言提示词内容。

**备选方案**

- 保留分支但加注释说明：无法解决覆盖假象，测试依旧测不到真实路径。
- 给 mock 一个"演示模式"开关：等于把同一个后门换个名字，问题不变。

**理由**

Mock 的价值在于**确定性**，不在于"看起来聪明"。凡是与模型语义能力无关的环节
（切分、入库、排序、过滤、引用装配、拒答判定）都能用构造向量确定性地断言；
真正需要语义能力的只有 M4 的效果评测，那里本来就必须用真实模型。

**代价**

离线演示时 mock 的检索结果不再"看起来相关"（哈希向量本就语义无关），
生成的回答是 mock 的回声文本。这是诚实的表现，不应通过特判掩盖。
演示需要真实效果时，配置真实 provider。

**回滚方式**

无需回滚。若将来确需差异化行为，应通过显式配置项表达，并让该配置在测试中被覆盖，
而不是依赖 provider 名字。

---

## ADR-0010 认证凭据使用 httpOnly Cookie 而非 localStorage

- 日期：2026-08-02
- 状态：已采纳

**背景**

M2 需要让浏览器持有短期 JWT。浏览器端常见做法是把 Token 放在 localStorage 后由
JavaScript 拼接 `Authorization` 请求头，或由服务端通过 Cookie 下发。前者会让任何成功执行的
XSS 脚本直接读取并带走长期可复用的凭据。

**决定**

登录成功后只通过名为 `access_token` 的 Cookie 下发 JWT，不在响应体返回 Token。Cookie 使用
`HttpOnly`、`SameSite=Lax` 和 `Path=/`；`APP_ENV=production` 时增加 `Secure`。前端请求使用
`credentials: "include"`，CORS 只配置显式来源，不使用 `*`。JWT 必须含过期时间，并通过
`JWT_SECRET`、`JWT_ALGORITHM`、`ACCESS_TOKEN_EXPIRE_MINUTES` 创建和校验。

**备选方案**

- localStorage + Bearer Token：接入简单，但 XSS 可以直接读取并外传凭据。
- 服务端随机 Session ID：便于主动失效，但需要 Redis 或数据库维护会话状态，本阶段会增加状态
  存储与清理机制。

**理由**

httpOnly Cookie 把凭据从 JavaScript 可读空间移除，降低 XSS 造成凭据外泄的风险；短期签名 JWT
保留当前无状态校验方式，不提前引入会话存储。

**代价**

浏览器会自动携带 Cookie，因此引入 CSRF 面。当前 `SameSite=Lax` 会阻止大多数跨站 POST 请求
携带 Cookie，同时保留同站部署和普通导航体验；所有状态变更接口也使用非 GET 方法。它不是完整
的 CSRF 方案：未来若前后端需要跨站部署、开放第三方嵌入或出现更敏感操作，应增加 CSRF Token
或严格校验 `Origin`/`Referer`。JWT 在到期前也无法单独撤销，后续如需强制下线再引入服务端会话
或 Token 吊销表。

**回滚方式**

如需可撤销会话，可保持 Cookie 和 API 响应契约不变，把 Cookie 内容替换为服务端 Session ID；
前端无需改为读取 Token。

---

## ADR-0011 Agent 工具调用层手写编排，并把 tool calling 纳入 Provider 协议

- 日期：2026-10-10
- 状态：已采纳

**背景**

M1 已交付「检索 → 带引用生成 → 低置信拒答」的单轮链路。要把它变成 Agent 应用，模型必须能
主动调用工具（检索、文档元数据、计算器），并在多步之间维护消息历史。可选路径有两条：引入
LangGraph / AutoGen 等编排框架，或在本仓库手写循环。

**决定**

1. 把 tool calling 纳入 `LLMProvider` 协议：新增 `complete_with_tools(messages, tools)`，返回
   `ToolCallResult`；`complete` / `stream` 保持不变。业务代码仍不按厂商名分支（延续 ADR-0009）。
2. 编排循环手写实现于 `app/rag/agent/`，不引入外部编排依赖。工具以 JSON Schema 暴露
   （`ToolRegistry.specs()`），按名执行；任何工具失败都转成可读错误回给模型，不向上抛。
3. 三个工具：`search_knowledge_base`（复用 `VectorSearchService`）、`get_document_meta`、
   `calculator`（AST 白名单求值，不使用 `eval`）。
4. 循环步数上限默认 4；超限不返回半成品，直接走既有拒答文案。纯寒暄短路，不触发检索。
5. Mock Provider 提供确定性的 `complete_with_tools`（首轮请求检索、拿到工具结果后作答），
   使整条 Agent 链路可以零成本、确定性断言（延续 mock-first 约定）。

**备选方案**

- LangGraph / AutoGen：表达力强，但引入重依赖与版本风险；当前仅 3 个工具、单层循环，收益不足。
- 在业务层判断 provider 名字走不同路径：违反 ADR-0009。

**理由**

手写循环让每一步可测试、可解释、可审计；协议扩展保持厂商可替换；mock 脚本让 CI 不依赖付费服务。

**代价**

手写循环没有框架自带的可视化、持久化与并行工具调用。当工具数量与分支复杂度上升（并行调用、
子图、人机确认）时应重新评估是否迁移到 LangGraph。工具参数由模型生成，因此工具层必须做白名单
校验（`calculator` 已按 AST 白名单实现，拒绝属性访问、下标、函数调用等一切其他语法）。

---

## ADR-0012 MimirQ 企业级检索中台接入（路线 B：微服务解耦集成）

- 日期：2026-11-11
- 状态：已采纳

**背景**

为评估及利用专业开源检索框架 MimirQ 提供的混合检索（向量 + BM25 稀疏检索 + 重排序 Reranker + 结构化多模态解析），企业知识库系统需要接入 MimirQ。若直接重构本系统内部存储层或全量替换，风险高、耦合重且破坏现有单元测试。

**决定**

1. 采用**路线 B（微服务中台接入模式）**：已部署运行的 MimirQ 实例作为独立检索与入库中台，通过标准 REST API 对接。
2. 保持本系统的业务层（`GroundedAnswerService`）完全解耦，定义 `MimirQSearchService` 遵循与既有 `VectorSearchService` 一致的搜索契约：
   `search(session, knowledge_base_id, query, top_k, min_score) -> tuple[SearchResult, ...]`。
3. 封装专用异步 HTTP 客户端 `MimirQClient`，使用 `httpx.AsyncClient(trust_env=False)` 负责 JWT 自动登录鉴权、Token 缓存刷新、混合检索代理（`/api/v1/rag/retrieve`）及文档代理上传。
4. 在配置中心 `Settings` 中新增 `MIMIRQ_ENABLED` 开关，支持通过环境变量一键在本地 pgvector 检索与 MimirQ 中台检索之间平滑切换。

**备选方案**

- 路线 A（深度源码融合）：直接修改本仓库代码库将 MimirQ 核心代码搬入。代价：引入 MimirQ 超过 200 个重型依赖，代码耦合过重，后续 MimirQ 上游升级困难。
- 路线 C（纯反向代理）：仅在前端跳转到 MimirQ Web 界面。代价：本系统自有的权限体系、会话管理和审计追踪能力无法复用。

**理由**

微服务方案保持了主系统的轻量与稳定性；`MimirQSearchService` 实现了零侵入适配，所有既有 110 项自动化测试依然 100% 通过，并新增专门的 MimirQ 单元与集成测试。

**代价**

检索阶段多一层跨服务的 HTTP 网络调用（局域网/本机通信延迟通常在 5~15ms 之间）。需保持 MimirQ 服务的健康运行。

**回滚方式**

将环境变量 `MIMIRQ_ENABLED=false` 即可即时回退到本系统自带的 pgvector 向量检索服务。

