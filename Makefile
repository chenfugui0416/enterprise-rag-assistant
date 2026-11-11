# 企业级 RAG 智能助手 — 统一命令入口
# 所有目标均可实际执行；若某目标暂不可用，会明确报错而不是静默通过。

SHELL := /bin/bash
API_DIR := apps/api
WEB_DIR := apps/web
VENV := $(API_DIR)/.venv
PY := $(VENV)/bin/python
COMPOSE := docker compose

.DEFAULT_GOAL := help
.PHONY: help setup env venv-api deps-web up-infra dev dev-api dev-web lint lint-api lint-web \
        format test test-api e2e e2e-install build up down clean ps logs

help: ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- 初始化

env: ## 从 .env.example 生成 .env（已存在则跳过）
	@if [ ! -f .env ]; then cp .env.example .env; echo "已创建 .env，请按需填写"; \
	else echo ".env 已存在，跳过"; fi

venv-api: ## 安装后端依赖
	@command -v uv >/dev/null || { echo "缺少 uv：curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	cd $(API_DIR) && uv venv --python 3.13 && uv pip install -e ".[dev]"

deps-web: ## 安装前端依赖
	cd $(WEB_DIR) && npm install

setup: env venv-api deps-web ## 一次性完成本地环境准备
	@echo ""
	@echo "环境就绪。下一步：make dev"

# ---------------------------------------------------------------- 开发

up-infra: ## 只启动 PostgreSQL(pgvector) 与 Redis
	$(COMPOSE) up -d db redis

dev-api: ## 单独启动后端（热重载）
	cd $(API_DIR) && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## 单独启动前端（热重载）
	cd $(WEB_DIR) && npm run dev

dev: up-infra ## 启动基础设施 + 前后端热重载（Ctrl-C 一并退出）
	@bash scripts/dev.sh

# ---------------------------------------------------------------- 质量门

lint-api: ## 后端格式与静态检查
	cd $(API_DIR) && .venv/bin/ruff check . && .venv/bin/ruff format --check .

lint-web: ## 前端 lint 与类型检查
	cd $(WEB_DIR) && npm run lint && npm run typecheck

lint: lint-api lint-web ## 全部静态检查

format: ## 自动修复可修复的格式问题
	cd $(API_DIR) && .venv/bin/ruff check --fix . && .venv/bin/ruff format .

test-api: ## 后端测试（默认 mock provider，无需 API Key）
	cd $(API_DIR) && .venv/bin/python -m pytest

test: test-api ## 全部单元/集成测试

benchmark: ## 执行 RAG 评测基准与 A/B 对比
	cd $(API_DIR) && .venv/bin/python scripts/run_benchmark.py

e2e-install: ## 安装 Playwright 浏览器（首次执行 e2e 前需要）
	cd $(WEB_DIR) && npx playwright install --with-deps chromium

e2e: ## 端到端测试：自动拉起前后端并验证真实页面
	cd $(WEB_DIR) && npm run e2e

# ---------------------------------------------------------------- 容器

build: ## 构建全部镜像
	$(COMPOSE) build

up: ## 以容器方式启动全栈
	$(COMPOSE) up -d --build
	@echo "前端 http://localhost:3000    后端 http://localhost:8000/docs"

ps: ## 查看容器状态
	$(COMPOSE) ps

logs: ## 跟踪容器日志
	$(COMPOSE) logs -f --tail=100

down: ## 停止全部容器（保留数据卷）
	$(COMPOSE) down

clean: ## 停止容器并删除数据卷（会清空数据库）
	$(COMPOSE) down -v
