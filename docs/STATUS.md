# 项目状态

> 最后更新：2026-08-01
> 当前里程碑：**M0 工程骨架**（基本完成，两项待验证）

## 一句话状态

后端、前端、测试、e2e、编排配置与 CI 定义均已就位并在本机实跑通过；
Docker 镜像构建与 pgvector 实际启动尚未验证，因为本机 Docker daemon 未就绪。

## 已完成并验证

| 项目 | 验证命令 | 真实结果 |
|---|---|---|
| 后端单元/集成测试 | `cd apps/api && .venv/bin/python -m pytest` | 13 passed |
| 后端静态检查 | `.venv/bin/ruff check .` | All checks passed |
| 后端格式检查 | `.venv/bin/ruff format --check .` | 25 files already formatted |
| 前端 lint | `cd apps/web && npm run lint` | 0 problems |
| 前端类型检查 | `npm run typecheck` | 通过，无错误 |
| 前端生产构建 | `npm run build` | 成功，`/` 与 `/_not-found` 静态预渲染 |
| 前端依赖漏洞 | `npm audit` | found 0 vulnerabilities |
| 端到端测试 | `npm run e2e` | 2 passed |
| 开发编排配置 | `docker compose config --quiet` | 通过 |
| 生产编排配置 | `docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet` | 通过 |
| 后端接口手工验证 | `curl -i http://127.0.0.1:8100/health` | HTTP 200，返回 mock provider 信息 |
| CORS 配置 | `curl -H "Origin: http://127.0.0.1:3100" .../health` | 正确返回 `access-control-allow-origin` |

## 当前能力边界（不要超出这个范围描述项目）

- 后端只有 `/health` 一个端点，**没有任何 RAG 功能**。
- 没有数据库表、没有迁移、没有认证、没有文档上传。
- Provider 层已具备切换真实厂商的能力，但**默认且仅验证过 mock 实现**。
- 前端只有一个首页，展示后端连通性与里程碑列表。
- 尚无任何检索命中率、延迟等评测数字。

## 已知问题

1. **Docker daemon 未就绪（阻塞 M0-13）**
   Docker Desktop 进程已启动，但 `docker info` 持续失败，`/Users/wind/.docker/run/docker.sock`
   不存在。需要在本机 Docker Desktop 界面完成启动或授权后，重新执行验证。
   影响：`docker build`、`make up`、pgvector 扩展是否真正可用，均未经实际验证。

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
4. 进入 M1：数据模型与迁移 → 文档解析 → 切分 → 向量化入库 → 检索 → 带引用生成。
